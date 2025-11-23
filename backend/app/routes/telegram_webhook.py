import logging
import tempfile
from typing import Any, Dict, Tuple

import httpx
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from backend.app.config import Settings, get_settings
from backend.app.core.router.intents import dispatch_message, normalize_text
from backend.app.models.schemas import NormalizedMessage
from backend.app.services import response_service, stt_service

router = APIRouter(prefix="/webhook/telegram", tags=["telegram"])
logger = logging.getLogger("elo.telegram")


async def _validate_secret(request: Request, settings: Settings) -> bool:
    secret = settings.telegram_webhook_secret
    if not secret:
        return True
    header_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if header_token != secret:
        logger.warning("[TELEGRAM] Secret inválido no webhook.")
        return False
    return True


async def _get_file_path(file_id: str, settings: Settings) -> str | None:
    if settings.telegram_sandbox_mode:
        logger.info("[TELEGRAM] Sandbox ativo: não buscando file_path para %s", file_id)
        return None
    if not settings.telegram_bot_token:
        logger.warning("[TELEGRAM] BOT_TOKEN ausente, não é possível baixar mídia.")
        return None

    url = f"{settings.telegram_base_url.rstrip('/')}/bot{settings.telegram_bot_token}/getFile"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params={"file_id": file_id})
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                logger.error("[TELEGRAM] getFile falhou: %s", data)
                return None
            return data["result"].get("file_path")
    except Exception:
        logger.exception("[TELEGRAM] Erro ao chamar getFile")
        return None


async def _download_file(file_id: str, settings: Settings) -> Tuple[bytes | None, str | None, str | None]:
    file_path = await _get_file_path(file_id, settings)
    if not file_path or not settings.telegram_bot_token:
        return None, None, None

    download_url = f"{settings.telegram_base_url.rstrip('/')}/file/bot{settings.telegram_bot_token}/{file_path}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(download_url)
            resp.raise_for_status()
            mime_type = resp.headers.get("content-type")
            return resp.content, download_url, mime_type
    except Exception:
        logger.exception("[TELEGRAM] Falha ao baixar arquivo file_id=%s", file_id)
        return None, None, None


async def _extract_media(message: Dict[str, Any], settings: Settings) -> Tuple[str, bytes | None, str | None, str | None]:
    """
    Retorna (tipo, bytes, url, mime)
    """
    if "photo" in message:
        photos = message["photo"] or []
        if photos:
            file_id = photos[-1]["file_id"]
            media_bytes, media_url, mime_type = await _download_file(file_id, settings)
            return "image", media_bytes, media_url, mime_type or "image/jpeg"

    if "document" in message:
        doc = message["document"] or {}
        file_id = doc.get("file_id")
        if file_id:
            media_bytes, media_url, mime_type = await _download_file(file_id, settings)
            if not mime_type and doc.get("mime_type"):
                mime_type = doc.get("mime_type")
            return "file", media_bytes, media_url, mime_type

    if "voice" in message:
        voice = message["voice"] or {}
        file_id = voice.get("file_id")
        if file_id:
            media_bytes, media_url, mime_type = await _download_file(file_id, settings)
            if not mime_type and voice.get("mime_type"):
                mime_type = voice.get("mime_type")
            return "audio", media_bytes, media_url, mime_type or "audio/ogg"

    if "audio" in message:
        audio = message["audio"] or {}
        file_id = audio.get("file_id")
        if file_id:
            media_bytes, media_url, mime_type = await _download_file(file_id, settings)
            if not mime_type and audio.get("mime_type"):
                mime_type = audio.get("mime_type")
            return "audio", media_bytes, media_url, mime_type

    return "text", None, None, None


async def _transcribe_if_audio(normalized_type: str, media_bytes: bytes | None) -> str | None:
    if normalized_type != "audio" or not media_bytes:
        return None

    try:
        with tempfile.NamedTemporaryFile(delete=True, suffix=".ogg") as tmp:
            tmp.write(media_bytes)
            tmp.flush()
            return await stt_service.transcribe_audio(tmp.name)
    except Exception:
        logger.exception("[TELEGRAM] Falha ao transcrever áudio.")
        return None


@router.post("")
async def telegram_webhook(request: Request) -> JSONResponse:
    settings = get_settings()

    if not await _validate_secret(request, settings):
        return JSONResponse({"status": "forbidden"}, status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        payload = await request.json()
    except Exception:
        logger.exception("[TELEGRAM] JSON inválido recebido.")
        return JSONResponse({"status": "error", "reason": "bad_json"}, status_code=400)

    if settings.telegram_sandbox_mode:
        logger.info("[TELEGRAM] payload simplificado recebido: %s", payload)

    message = payload.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not chat_id:
        return JSONResponse({"status": "ignored", "reason": "no_chat"})

    user_id = f"tg:{chat_id}"
    text = message.get("text") or message.get("caption") or ""

    normalized_type, media_bytes, media_url, mime_type = await _extract_media(message, settings)

    if normalized_type == "audio" and media_bytes:
        transcript = await _transcribe_if_audio(normalized_type, media_bytes)
        if transcript:
            text = transcript

    normalized_text = normalize_text(text) if text else ""

    normalized_message = NormalizedMessage(
        user_id=user_id,
        type=normalized_type,
        text=normalized_text or None,
        media_url=media_url,
        media_bytes=media_bytes,
        mime_type=mime_type,
        provider="telegram",
    )

    # Handler específico para /start
    if normalized_text == "/start":
        greeting_text = (
            "Olá! Eu sou o ELO, seu assistente virtual. "
            "Estou aqui para te ajudar a entender documentos, leis e serviços públicos de um jeito simples e direto. "
            "Pode me mandar áudio, imagem ou texto que eu te respondo. Como posso te ajudar hoje?"
        )
        try:
            await response_service.responder_usuario(
                to=user_id,
                text=greeting_text,
                mode="texto+audio",  # Envia áudio e texto
                context=normalized_message,
            )
            return JSONResponse({"status": "ok", "delivered": True, "intent": "start"})
        except Exception:
            logger.exception("[TELEGRAM] Falha ao enviar saudação inicial.")
            return JSONResponse({"status": "error", "reason": "greeting_failed"}, status_code=500)

    try:
        routed = await dispatch_message(normalized_message)
        reply = routed.get("text") or "Estou aqui para ajudar."
        intent = routed.get("intent")
        already_delivered = bool(routed.get("delivered"))
    except Exception:
        logger.exception("[TELEGRAM] Falha ao processar intenção.")
        return JSONResponse(
            {"status": "ok", "delivered": False, "reason": "intent_error"},
            status_code=200,
        )

    try:
        delivered = already_delivered
        if not already_delivered:
            # Detecta se o usuário pediu áudio explicitamente no texto
            audio_keywords = ["audio", "áudio", "voz", "falar", "ouvir", "fala", "explique falando"]
            user_wants_audio = any(k in normalized_text for k in audio_keywords)
            
            mode = "texto+audio" if (normalized_type == "audio" or settings.send_audio_default or user_wants_audio) else "texto"
            await response_service.responder_usuario(
                to=user_id,
                text=reply,
                mode=mode,
                context=normalized_message,
            )
            delivered = True
    except Exception:
        logger.exception("[TELEGRAM] Falha ao enviar resposta.")
        return JSONResponse(
            {
                "status": "ok",
                "delivered": False,
                "reason": "provider_error",
                "answer_preview": reply,
                "intent": intent,
            },
            status_code=200,
        )

    return JSONResponse(
        {
            "status": "ok",
            "delivered": delivered,
            "answer_preview": reply,
            "intent": intent,
        }
    )
