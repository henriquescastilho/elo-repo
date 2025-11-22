"""
High-level TTS helper for ELO.
"""

from typing import Any

from backend.app.services import tts_service


async def synthesize(text: str, context: Any) -> str:
    """
    Generate TTS audio and return a public URL or media handle compatible with WAHA.
    """
    return await tts_service.generate_tts_and_upload(text, context)
