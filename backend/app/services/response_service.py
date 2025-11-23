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


from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Retry configuration: 3 attempts, exponential wait 1s -> 2s -> 4s
RETRY_CONFIG = {
    "stop": stop_after_attempt(3),
    "wait": wait_exponential(multiplier=1, min=1, max=10),
    "retry": retry_if_exception_type(Exception),
    "reraise": True,
}

async def _try_send(provider: str, to: str, text: str = "", audio_url: str | None = None) -> None:
    """Attempt to send via a specific provider."""
    logger.info("Tentando enviar via %s para %s", provider, to)
    if provider == "twilio":
        await whatsapp_provider_twilio.send_message(text=text, audio_url=audio_url, user_id=to)
    elif provider == "console":
        if audio_url:
            await whatsapp_provider_console.send_message(text=text, audio_url=audio_url, user_id=to)
        else:
            await whatsapp_provider_console.send_text_message(user_id=to, text=text)
    else: # waha
        if audio_url:
            await whatsapp_provider_waha.send_message(text=text, audio_url=audio_url, user_id=to)
        else:
            await whatsapp_provider_waha.send_text_message(user_id=to, text=text)

@retry(**RETRY_CONFIG)
async def _send_with_retry(provider: str, to: str, text: str = "", audio_url: str | None = None) -> None:
    await _try_send(provider, to, text, audio_url)

async def _send_robust(to: str, text: str = "", audio_url: str | None = None) -> str:
    """Send with retry and fallback to Twilio if WAHA fails."""
    settings = get_settings()
    primary_provider = (settings.whatsapp_provider or "waha").lower()
    
    # Console provider never falls back
    if primary_provider == "console":
        await _try_send("console", to, text, audio_url)
        return "console"

    try:
        await _send_with_retry(primary_provider, to, text, audio_url)
        logger.info("Mensagem enviada com sucesso via %s", primary_provider)
        return primary_provider
    except Exception as exc:
        logger.warning("Falha no provider primário %s: %s. Tentando fallback Twilio.", primary_provider, exc)
        
        # Fallback to Twilio if configured
        if settings.twilio_account_sid:
            try:
                await _send_with_retry("twilio", to, text, audio_url)
                logger.info("Mensagem enviada com sucesso via fallback Twilio")
                return "twilio"
            except Exception as exc_twilio:
                logger.error("Falha no fallback Twilio: %s", exc_twilio)
                raise exc_twilio
        else:
            logger.error("Fallback Twilio não configurado.")
            raise exc

async def responder_usuario(to: str, text: str, mode: str = "auto", context: Any | None = None) -> dict:
    """
    Always send text; optionally synthesize and send audio.
    mode: "texto" | "texto+audio" | "auto" (usa settings.send_audio_default).
    """
    settings = get_settings()
    
    # Send Text
    provider_used = await _send_robust(to, text=text)
    
    audio_sent = False
    if _should_send_audio(mode, settings):
        try:
            audio_url = await tts_core.synthesize(text, context)
            # Send Audio (separate message usually)
            await _send_robust(to, audio_url=audio_url)
            audio_sent = True
        except Exception as exc:
            logger.warning("Falha ao enviar áudio: %s", exc)
            # Don't fail the whole response if audio fails, text was already sent

    return {"provider": provider_used, "audio_sent": audio_sent}

