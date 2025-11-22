"""WAHA WhatsApp provider integration using centralized client."""

import logging

from backend.app.config import get_settings
from backend.app.core.exceptions import ProviderError
from backend.app.core.logging import get_logger
from backend.app.infra import waha_client

logger = get_logger(__name__)


async def send_message(text: str, audio_url: str | None, user_id: str) -> None:
    settings = get_settings()
    if not settings.waha_base_url or not settings.waha_api_token:
        raise ProviderError("WAHA configuration missing.")

    session_name = getattr(settings, "waha_session_name", "default") or "default"
    if text:
        logger.info("Enviando texto via WAHA user=%s", user_id)
        await waha_client.send_text(user_id, text, session=session_name)
    if audio_url:
        logger.info("Enviando áudio via WAHA user=%s", user_id)
        await waha_client.send_voice(user_id, audio_url, session=session_name)


async def send_text_message(user_id: str, text: str) -> None:
    await send_message(text=text, audio_url=None, user_id=user_id)
