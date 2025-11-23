"""Utilities to send responses (texto e áudio) para os canais suportados."""

import logging
import os
from pathlib import Path
from typing import Any, Tuple
from urllib.parse import urlparse

import httpx

from backend.app.config import Settings, get_settings
from backend.app.core.tts import service as tts_core
from backend.app.services import (
    telegram_provider,
    whatsapp_provider_console,
    whatsapp_provider_twilio,
    whatsapp_provider_waha,
)

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
    is_telegram, chat_id = _resolve_telegram_target(to, context)
    if is_telegram:
        return await _responder_telegram(chat_id, to, text, mode, context)

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


def _resolve_telegram_target(to: str, context: Any | None) -> Tuple[bool, str]:
    """
    Verifica se a mensagem deve ser enviada via Telegram.
    - user_id com prefixo tg:
    - context.provider == 'telegram'
    Retorna (is_telegram, chat_id_sem_prefixo)
    """
    if to.startswith("tg:"):
        return True, to.removeprefix("tg:")

    provider = getattr(context, "provider", None)
    if provider and provider.lower() == "telegram":
        chat_id = getattr(context, "user_id", to)
        chat_id = str(chat_id)
        if chat_id.startswith("tg:"):
            chat_id = chat_id.removeprefix("tg:")
        return True, chat_id

    return False, to


async def _load_bytes_from_url(url: str) -> bytes | None:
    """Busca bytes a partir de uma URL http(s) ou caminho local resolvido pelo /media."""
    parsed = urlparse(url)
    if parsed.scheme in ("", "file"):
        path = Path(url.replace("file://", ""))
        if path.exists():
            return path.read_bytes()

    media_root = Path(os.getcwd())
    if parsed.path.startswith("/media/"):
        candidate = media_root / parsed.path.lstrip("/")
        if candidate.exists():
            return candidate.read_bytes()

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
    except Exception:
        logger.warning("Não foi possível baixar mídia para Telegram: %s", url)
        return None


async def _responder_telegram(chat_id: str, user_ref: str, text: str, mode: str, context: Any | None) -> dict:
    """
    Envia respostas via Telegram, respeitando sandbox e não afetando WAHA.
    """
    await telegram_provider.send_text(chat_id, text)

    audio_sent = False
    settings = get_settings()
    if _should_send_audio(mode, settings):
        try:
            audio_url = await tts_core.synthesize(text, context)
            audio_bytes = await _load_bytes_from_url(audio_url)
            if audio_bytes:
                filename = Path(urlparse(audio_url).path).name or "audio.ogg"
                await telegram_provider.send_audio(chat_id, audio_bytes, filename=filename)
                audio_sent = True
            else:
                logger.warning("[TELEGRAM] Falha ao obter bytes do áudio para %s", user_ref)
        except Exception:
            logger.exception("[TELEGRAM] Erro ao enviar áudio para %s", user_ref)

    return {"provider": "telegram", "audio_sent": audio_sent}
