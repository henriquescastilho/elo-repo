"""
Utilities to send responses (text and optional audio) to WhatsApp users.
"""

import logging
from typing import Any

from backend.app.config import Settings, get_settings
from backend.app.core.tts import service as tts_core
from backend.app.services import whatsapp_provider_twilio, whatsapp_provider_waha, whatsapp_provider_console

logger = logging.getLogger(__name__)


def _should_send_audio(mode: str, settings: Settings) -> bool:
    if mode == "texto":
        return False
    if mode == "texto+audio":
        return True
    return bool(settings.send_audio_default)


async def responder_usuario(to: str, text: str, mode: str = "auto", context: Any | None = None) -> dict:
    """
    Always send text; optionally synthesize and send audio.
    mode: "texto" | "texto+audio" | "auto" (usa settings.send_audio_default).
    """
    settings = get_settings()
    provider = (settings.whatsapp_provider or "waha").lower()

    await _send_text(provider, to, text)
    audio_sent = False

    if _should_send_audio(mode, settings):
        audio_url = await tts_core.synthesize(text, context)
        await _send_audio(provider, to, audio_url)
        audio_sent = True

    return {"provider": provider, "audio_sent": audio_sent}


async def _send_text(provider: str, to: str, text: str) -> None:
    if provider == "twilio":
        await whatsapp_provider_twilio.send_message(text=text, audio_url=None, user_id=to)
    elif provider == "console":
        await whatsapp_provider_console.send_text_message(user_id=to, text=text)
    else:
        await whatsapp_provider_waha.send_text_message(user_id=to, text=text)


async def _send_audio(provider: str, to: str, audio_url: str) -> None:
    if provider == "twilio":
        fallback_text = "Segue o áudio com a resposta do ELO."
        await whatsapp_provider_twilio.send_message(text=fallback_text, audio_url=audio_url, user_id=to)
    elif provider == "console":
        await whatsapp_provider_console.send_message(text="", audio_url=audio_url, user_id=to)
    else:
        await whatsapp_provider_waha.send_message(text="", audio_url=audio_url, user_id=to)

