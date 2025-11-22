"""Twilio WhatsApp provider integration placeholder."""

import base64
import logging
from typing import Any

import httpx

from backend.app.config import get_settings
from backend.app.core.exceptions import ProviderError

logger = logging.getLogger(__name__)


async def send_message(text: str, audio_url: str | None, user_id: str) -> None:
    settings = get_settings()
    if not (
        settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_whatsapp_number
    ):
        raise ProviderError("Twilio configuration missing.")

    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{settings.twilio_account_sid}/Messages.json"
    )
    payload: dict[str, Any] = {
        "To": f"whatsapp:{user_id}",
        "From": f"whatsapp:{settings.twilio_whatsapp_number}",
        "Body": text,
    }
    if audio_url:
        payload["MediaUrl"] = audio_url

    credentials = f"{settings.twilio_account_sid}:{settings.twilio_auth_token}".encode()
    auth_header = base64.b64encode(credentials).decode()
    headers = {"Authorization": f"Basic {auth_header}"}

    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, data=payload, headers=headers, timeout=10)
    except Exception as exc:  # pragma: no cover - external integration
        logger.error("Twilio send_message failed: %s", exc)
        raise ProviderError("Failed to deliver message via Twilio") from exc


async def send_text_message(user_id: str, text: str) -> None:
    await send_message(text=text, audio_url=None, user_id=user_id)
