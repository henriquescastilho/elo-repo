import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.app.config import get_settings
from backend.app.core.router.intents import dispatch_message, normalize_text
from backend.app.models.schemas import NormalizedMessage
from backend.app.services import response_service

router = APIRouter()
logger = logging.getLogger("elo.whatsapp")


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request) -> JSONResponse:
    """Webhook WAHA filtrado que responde apenas mensagens diretas do usuário."""
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

    msg_from = payload.get("from")
    msg_to = payload.get("to")
    msg_body = payload.get("body", "").strip()
    from_me = payload.get("fromMe", False)

    if from_me:
        return JSONResponse({"status": "ignored", "reason": "from_me"})

    ILLEGAL_SENDERS = ("@newsletter", "@g.us", "@broadcast")
    if msg_from and any(tag in msg_from for tag in ILLEGAL_SENDERS):
        logger.info("[WAHA] Ignorando mensagem automática/canal: %s", msg_from)
        return JSONResponse({"status": "ignored", "reason": "not_direct_chat"})

    if bot_id and msg_to != bot_id:
        logger.info("[WAHA] Ignorando mensagem que não é para o bot: to=%s bot=%s", msg_to, bot_id)
        return JSONResponse({"status": "ignored", "reason": "wrong_target"})

    if not msg_body:
        return JSONResponse({"status": "ignored", "reason": "empty_message"})

    user_id = msg_from
    normalized_text = normalize_text(msg_body)
    logger.info("[WAHA] Mensagem válida de %s: %s", user_id, normalized_text)

    normalized_message = NormalizedMessage(user_id=user_id, type="text", text=normalized_text)
    try:
        routed = await dispatch_message(normalized_message)
        reply = routed.get("text") or "Estou aqui para ajudar."
        already_delivered = bool(routed.get("delivered"))
    except Exception:
        logger.exception("[WAHA] Falha ao processar intenção")
        return JSONResponse(
            {"status": "ok", "delivered": False, "reason": "intent_error"},
            status_code=200,
        )

    try:
        if not already_delivered:
            settings = get_settings()
            mode = "texto+audio" if settings.send_audio_default else "texto"
            await response_service.responder_usuario(
                to=user_id,
                text=reply,
                mode=mode,
                context=normalized_message,
            )
    except Exception:
        logger.exception("[WAHA] Falha ao enviar resposta")
        return JSONResponse(
            {"status": "ok", "delivered": False, "reason": "provider_error"},
            status_code=200,
        )

    return JSONResponse({"status": "ok", "delivered": True})
