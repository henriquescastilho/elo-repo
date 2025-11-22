"""Speech-to-text service using OpenAI Whisper (Audio -> Transcriptions)."""

import logging
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

import httpx

from backend.app.config import Settings, get_settings

logger = logging.getLogger(__name__)
FALLBACK_STT_MESSAGE = "Não consegui entender esse áudio. Pode tentar falar de novo?"


async def _download_audio(audio_url: str) -> Optional[bytes]:
    if audio_url.startswith("http"):
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(audio_url)
            if response.status_code >= 400:
                logger.warning("Falha ao baixar áudio: status=%s", response.status_code)
                return None
            return response.content
    path = Path(audio_url)
    if not path.exists():
        logger.warning("Caminho de áudio não encontrado: %s", audio_url)
        return None
    return path.read_bytes()


async def _call_stt_openai(audio_bytes: bytes, filename: str, settings: Settings) -> Tuple[str, bool]:
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY ausente para STT; usando fallback.")
        return FALLBACK_STT_MESSAGE, False
    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.warning("SDK OpenAI não está instalado para STT.")
        return FALLBACK_STT_MESSAGE, False

    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_api_base or "https://api.openai.com/v1",
    )
    model = getattr(settings, "stt_model_name", None) or "whisper-1"
    audio_file = BytesIO(audio_bytes)
    audio_file.name = filename
    try:
        result = await client.audio.transcriptions.create(
            model=model,
            file=audio_file,
            language="pt",
        )
    except Exception as exc:  # pragma: no cover - external dependency
        logger.exception("OpenAI STT falhou: %s", exc)
        return FALLBACK_STT_MESSAGE, False
    text = getattr(result, "text", None) or ""
    if not text:
        return FALLBACK_STT_MESSAGE, False
    return text, True


async def transcribe_audio_url(audio_url: str) -> str:
    """Transcribe audio from a URL or local path using the configured STT provider."""
    settings = get_settings()
    provider = (settings.stt_provider or "openai").lower()
    logger.info("Transcribing audio via %s for url=%s", provider, audio_url)

    if provider != "openai":
        logger.warning("STT provider %s não suportado; usando fallback.", provider)
        return FALLBACK_STT_MESSAGE

    audio_bytes = await _download_audio(audio_url)
    if not audio_bytes:
        return FALLBACK_STT_MESSAGE

    filename = Path(audio_url).name or "audio.wav"
    text, success = await _call_stt_openai(audio_bytes, filename, settings)
    return text if success else FALLBACK_STT_MESSAGE
