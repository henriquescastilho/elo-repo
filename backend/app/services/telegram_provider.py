"""Provider para envio de mensagens via Telegram Bot API."""

import logging
from typing import Any

import httpx

from backend.app.config import get_settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


def _should_skip_send(settings) -> bool:
    if not settings.telegram_enabled:
        logger.info("[TELEGRAM] SANDBOX: envio desabilitado (TELEGRAM_ENABLED=False).")
        return True
    if settings.telegram_sandbox_mode:
        logger.info("[TELEGRAM] SANDBOX ativo: não enviando para API real.")
        return True
    return False


def _build_url(endpoint: str, base_url: str, token: str) -> str:
    return f"{base_url.rstrip('/')}/bot{token}/{endpoint.lstrip('/')}"


async def _post(endpoint: str, payload: dict[str, Any], files: dict[str, Any] | None = None) -> bool:
    settings = get_settings()
    if _should_skip_send(settings):
        return True

    token = settings.telegram_bot_token
    if not token:
        logger.error("[TELEGRAM] BOT_TOKEN ausente; não é possível enviar.")
        return False

    url = _build_url(endpoint, settings.telegram_base_url, token)
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, data=payload, files=files)
    except Exception:
        logger.exception("[TELEGRAM] Falha ao chamar endpoint %s", endpoint)
        return False

    if resp.status_code != 200:
        logger.error("[TELEGRAM] Erro HTTP status=%s body=%s", resp.status_code, resp.text)
        return False

    try:
        data = resp.json()
    except Exception:
        logger.error("[TELEGRAM] Resposta inválida: %s", resp.text)
        return False

    if not data.get("ok"):
        logger.error("[TELEGRAM] API respondeu erro: %s", data)
        return False

    return True


async def send_text(chat_id: str, text: str) -> bool:
    payload = {"chat_id": chat_id, "text": text}
    return await _post("sendMessage", payload)


async def send_audio(chat_id: str, audio_bytes: bytes, filename: str = "audio.ogg") -> bool:
    files = {"audio": (filename, audio_bytes)}
    payload = {"chat_id": chat_id}
    return await _post("sendAudio", payload, files=files)


async def send_image(chat_id: str, image_bytes: bytes, filename: str = "image.jpg") -> bool:
    files = {"photo": (filename, image_bytes)}
    payload = {"chat_id": chat_id}
    return await _post("sendPhoto", payload, files=files)
