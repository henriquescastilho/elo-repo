"""Text-to-speech generation using OpenAI Audio Speech."""

import logging
import uuid
from pathlib import Path
from typing import Any, Tuple

from backend.app.config import Settings, get_settings

logger = logging.getLogger(__name__)
FALLBACK_AUDIO_URL = "https://example.com/audio.mp3"


import os

def _tts_output_path() -> Tuple[Path, str]:
    # Use /app/media as default in Docker, or relative media in local dev
    # main.py mounts os.path.join(os.getcwd(), "media")
    # In Docker, cwd is /app.
    media_root = Path(os.getcwd()) / "media"
    tts_dir = media_root / "tts"
    tts_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{uuid.uuid4()}.mp3"
    return tts_dir / filename, filename


async def _call_tts_openai(text: str, settings: Settings) -> Tuple[str, bool]:
    provider = (settings.tts_provider or "openai").lower()
    client = None
    model = None
    voice = getattr(settings, "tts_voice", None) or "alloy"

    if provider == "azure":
        if not settings.azure_openai_api_key or not settings.azure_openai_endpoint:
            logger.warning("Azure OpenAI config missing for TTS.")
            return FALLBACK_AUDIO_URL, False
        try:
            from openai import AsyncAzureOpenAI
            client = AsyncAzureOpenAI(
                api_key=settings.azure_openai_api_key,
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
            )
            model = (
                settings.azure_tts_deployment_name
                or getattr(settings, "tts_model_name", None)
                or settings.azure_deployment_name
                or "gpt-4o-mini-tts"
            )
        except ImportError:
            logger.warning("OpenAI SDK not installed.")
            return FALLBACK_AUDIO_URL, False
    else:
        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY ausente para TTS; usando fallback.")
            return FALLBACK_AUDIO_URL, False
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_api_base or "https://api.openai.com/v1",
            )
            model = getattr(settings, "tts_model_name", None) or "gpt-4o-mini-tts"
        except ImportError:
            logger.warning("SDK OpenAI não está instalado para TTS.")
            return FALLBACK_AUDIO_URL, False

    output_path, filename = _tts_output_path()
    try:
        async with client.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice,
            input=text,
            response_format="mp3",
        ) as response:
            await response.stream_to_file(output_path)
    except Exception as exc:  # pragma: no cover - external dependency
        logger.exception("%s TTS falhou: %s", provider.upper(), exc)
        return FALLBACK_AUDIO_URL, False

    # Construct URL for WAHA
    # Assuming backend is accessible at 'backend' hostname in Docker network
    # Port 8000 is standard.
    # TODO: Make base URL configurable via settings
    api_url = getattr(settings, "api_public_url", "http://backend:8000")
    full_url = f"{api_url}/media/tts/{filename}"
    
    return full_url, True


async def generate_tts_and_upload(text: str, context: Any) -> str:
    """Generate TTS audio, store locally and return the path or URL usable by WAHA."""
    settings = get_settings()
    provider = (settings.tts_provider or "openai").lower()
    logger.info("Generating TTS via %s for user=%s", provider, getattr(context, "user_id", "unknown"))

    if provider in ("openai", "azure"):
        audio_ref, success = await _call_tts_openai(text, settings)
        return audio_ref if success else FALLBACK_AUDIO_URL

    logger.warning("Unsupported TTS provider '%s', usando fallback.", provider)
    return FALLBACK_AUDIO_URL
