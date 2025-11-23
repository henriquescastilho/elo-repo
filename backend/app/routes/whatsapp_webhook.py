import logging
import tempfile
from typing import Tuple

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.app.config import Settings, get_settings
from backend.app.core.router.intents import dispatch_message, normalize_text
from backend.app.models.schemas import NormalizedMessage
from backend.app.services import cache_service, response_service, stt_service

router = APIRouter()
logger = logging.getLogger("elo.whatsapp")


def _sanitize_type(raw_type: str | None) -> str:
    normalized = (raw_type or "text").lower()
    if normalized in ("ptt", "voice"):
        return "audio"
    if normalized in ("image", "photo", "sticker"):
        return "image"
    if normalized in ("document", "file", "pdf", "video", "ppt", "xls", "doc", "docx", "xlsx", "pptx"):
        return "file"
    return "text" if normalized in ("chat", "unknown") else normalized


async def _download_media(url: str, settings: Settings) -> Tuple[bytes | None, str | None]:
    headers = {}
    token = getattr(settings, "waha_api_token", None)
    if token:
        headers["X-API-Key"] = token

    mime_type = None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            mime_type = response.headers.get("content-type")
            return response.content, mime_type
    except Exception:
        logger.exception("[WAHA] Falha ao baixar mídia de %s", url)
        return None, None


async def _transcribe_audio_if_needed(media_bytes: bytes | None, settings: Settings) -> str | None:
    if not media_bytes:
        return None

    try:
        with tempfile.NamedTemporaryFile(delete=True, suffix=".ogg") as tmp:
            tmp.write(media_bytes)
            tmp.flush()
            return await stt_service.transcribe_audio(tmp.name)
    except Exception:
        logger.exception("[WAHA] Falha ao transcrever áudio")
        return None


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request) -> JSONResponse:
    """Webhook WAHA filtrado que responde mensagens diretas do usuário (texto, imagem, áudio)."""
    raw = await request.body()
    logger.info("[WAHA] RAW: %r", raw)

    try:
        data = await request.json()
        logger.info("[WAHA] JSON: %s", data)
    except Exception:
        logger.exception("[WAHA] JSON inválido")
        return JSONResponse({"status": "error", "reason": "bad_json"}, status_code=400)

    event = data.get("event")
    payload = data.get("payload") or {}
    me = data.get("me") or {}
    bot_id = me.get("id")

    if event not in ("message", "message.any"):
        return JSONResponse({"status": "ignored", "reason": "not_message_event"})

    settings = get_settings()
    msg_from = payload.get("from")
    msg_to = payload.get("to")
    msg_body = (payload.get("body") or "").strip()
    msg_type_raw = payload.get("type") or payload.get("messageType")
    from_me = payload.get("fromMe", False)
    media = payload.get("media") or {}
    media_url = media.get("url") or payload.get("mediaUrl")
    mime_type = media.get("mimetype") or payload.get("mimetype")
    has_media = bool(payload.get("hasMedia")) or bool(media_url)
    message_id = (
        payload.get("id")
        or payload.get("msgId")
        or payload.get("messageId")
        or payload.get("message_id")
        or (payload.get("key") or {}).get("id")
    )

    if from_me:
        return JSONResponse({"status": "ignored", "reason": "from_me"})

    ILLEGAL_SENDERS = ("@newsletter", "@g.us", "@broadcast")
    if msg_from and any(tag in msg_from for tag in ILLEGAL_SENDERS):
        logger.info("[WAHA] Ignorando mensagem automática/canal: %s", msg_from)
        return JSONResponse({"status": "ignored", "reason": "not_direct_chat"})

    if message_id:
        try:
            if await cache_service.is_duplicate_message(message_id):
                logger.info("[WAHA] Ignorando mensagem duplicada id=%s", message_id)
                return JSONResponse({"status": "ignored", "reason": "duplicate"})
        except Exception:
            logger.exception("[WAHA] Falha ao checar duplicidade de mensagem")

    if bot_id and msg_to != bot_id:
        logger.info("[WAHA] Ignorando mensagem que não é para o bot: to=%s bot=%s", msg_to, bot_id)
        return JSONResponse({"status": "ignored", "reason": "wrong_target"})

    # Se não houver texto nem mídia, ignore
    if not msg_body and not has_media:
        return JSONResponse({"status": "ignored", "reason": "empty_message"})

    normalized_type = _sanitize_type(msg_type_raw)
    media_bytes = None

    if has_media and media_url:
        media_bytes, resolved_mime = await _download_media(media_url, settings)
        mime_type = mime_type or resolved_mime

    if normalized_type == "audio":
        transcript = await _transcribe_audio_if_needed(media_bytes, settings)
        if transcript:
            msg_body = transcript
        else:
            msg_body = msg_body or "[Áudio recebido, mas não foi possível transcrever]"

    user_id = msg_from
    normalized_text = normalize_text(msg_body) if msg_body else ""
    logger.info("[WAHA] Mensagem válida de %s (type=%s, media=%s)", user_id, normalized_type, bool(media_url))

    normalized_message = NormalizedMessage(
        user_id=user_id,
        type=normalized_type if normalized_type in ("text", "audio", "image", "file") else "text",
        text=normalized_text or None,
        media_url=media_url,
        media_bytes=media_bytes,
        mime_type=mime_type,
    )
    try:
        routed = await dispatch_message(normalized_message)
        reply = routed.get("text") or "Estou aqui para ajudar."
        intent = routed.get("intent")
        already_delivered = bool(routed.get("delivered"))
    except Exception:
        logger.exception("[WAHA] Falha ao processar intenção")
        return JSONResponse(
            {"status": "ok", "delivered": False, "reason": "intent_error"},
            status_code=200,
        )

    try:
        if not already_delivered:
            # Se o usuário mandou áudio, respondemos com áudio também (espelhamento)
            # Ou se a configuração padrão for enviar áudio sempre.
            if normalized_type == "audio" or settings.send_audio_default:
                mode = "texto+audio"
            else:
                mode = "texto"

            await response_service.responder_usuario(
                to=user_id,
                text=reply,
                mode=mode,
                context=normalized_message,
            )
    except Exception:
        logger.exception("[WAHA] Falha ao enviar resposta")
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
            "delivered": True,
            "answer_preview": reply,
            "intent": intent,
        }
    )
