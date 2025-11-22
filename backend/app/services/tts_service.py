"""Text-to-speech generation using OpenAI Audio Speech."""

import logging
import uuid
from pathlib import Path
from typing import Any, Tuple

from backend.app.config import Settings, get_settings

logger = logging.getLogger(__name__)
FALLBACK_AUDIO_URL = "https://example.com/audio.mp3"


def _tts_output_path() -> Path:
    base = Path(__file__).resolve().parent.parent
    target = base / "media" / "tts"
    target.mkdir(parents=True, exist_ok=True)
    return target / f"{uuid.uuid4()}.mp3"


async def _call_tts_openai(text: str, settings: Settings) -> Tuple[str, bool]:
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY ausente para TTS; usando fallback.")
        return FALLBACK_AUDIO_URL, False
    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.warning("SDK OpenAI não está instalado para TTS.")
        return FALLBACK_AUDIO_URL, False

    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_api_base or "https://api.openai.com/v1",
    )
    model = getattr(settings, "tts_model_name", None) or "gpt-4o-mini-tts"
    voice = getattr(settings, "tts_voice", None) or "alloy"
    output_path = _tts_output_path()
    try:
        async with client.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice,
            input=text,
            response_format="mp3",
        ) as response:
            await response.stream_to_file(output_path)
    except Exception as exc:  # pragma: no cover - external dependency
        logger.exception("OpenAI TTS falhou: %s", exc)
        return FALLBACK_AUDIO_URL, False

    return str(output_path), True


async def generate_tts_and_upload(text: str, context: Any) -> str:
    """Generate TTS audio, store locally and return the path or URL usable by WAHA."""
    settings = get_settings()
    provider = (settings.tts_provider or "openai").lower()
    logger.info("Generating TTS via %s for user=%s", provider, getattr(context, "user_id", "unknown"))

    if provider == "openai":
        audio_ref, success = await _call_tts_openai(text, settings)
        return audio_ref if success else FALLBACK_AUDIO_URL

    logger.warning("Unsupported TTS provider '%s', usando fallback.", provider)
    return FALLBACK_AUDIO_URL
