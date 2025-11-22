"""
Thin WAHA HTTP client to centralize WhatsApp delivery (text/voice/image).
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Optional

import httpx

from backend.app.config import get_settings
from backend.app.core.exceptions import ProviderError
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1


def _build_headers(api_token: Optional[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    if api_token:
        headers["x-api-key"] = api_token
    return headers


def _get_session(settings) -> str:
    return getattr(settings, "waha_session_name", "default") or "default"


async def send_text(to: str, text: str, session: str | None = None) -> None:
    settings = get_settings()
    if not settings.waha_base_url or not settings.waha_api_token:
        raise ProviderError("WAHA configuration missing.")

    target_session = session or _get_session(settings)
    url = f"{settings.waha_base_url.rstrip('/')}/api/sendText"
    payload: dict[str, Any] = {"chatId": to, "text": text, "session": target_session}
    headers = _build_headers(settings.waha_api_token)
    await _post_with_retry(url, payload, headers)


async def _convert_voice_if_needed(
    client: httpx.AsyncClient,
    base_url: str,
    session: str,
    audio: bytes | None,
    headers: dict[str, str],
) -> str:
    url = f"{base_url.rstrip('/')}/api/{session}/media/convert/voice"
    files = {"file": ("audio", audio or b"", "application/octet-stream")}
    response = await client.post(url, files=files, headers=headers, timeout=30)
    if response.status_code >= 400:
        raise ProviderError(f"WAHA voice convert failed ({response.status_code})")
    data = response.json()
    return data.get("url") or data.get("audio") or ""


async def send_voice(
    to: str, audio: bytes | str, session: str | None = None
) -> None:
    settings = get_settings()
    if not settings.waha_base_url or not settings.waha_api_token:
        raise ProviderError("WAHA configuration missing.")

    target_session = session or _get_session(settings)
    base_url = settings.waha_base_url.rstrip("/")
    headers = _build_headers(settings.waha_api_token)

    audio_url = ""
    audio_bytes: bytes | None = None

    if isinstance(audio, bytes):
        audio_bytes = audio
    elif isinstance(audio, str):
        if audio.startswith("http"):
            audio_url = audio
        elif os.path.exists(audio):
            audio_bytes = Path(audio).read_bytes()
        else:
            audio_url = audio

    async with httpx.AsyncClient() as client:
        if audio_bytes is not None:
            audio_url = await _convert_voice_if_needed(
                client, base_url, target_session, audio_bytes, headers
            )

        if not audio_url:
            raise ProviderError("Audio payload missing or conversion failed.")

        url = f"{base_url}/api/sendVoice"
        payload: dict[str, Any] = {
            "chatId": to,
            "audio": audio_url,
            "session": target_session,
        }
        await _post_with_retry(url, payload, headers, client=client)


async def send_image(to: str, image_url: str, caption: str = "", session: str | None = None) -> None:
    settings = get_settings()
    if not settings.waha_base_url or not settings.waha_api_token:
        raise ProviderError("WAHA configuration missing.")

    target_session = session or _get_session(settings)
    url = f"{settings.waha_base_url.rstrip('/')}/api/sendImage"
    payload: dict[str, Any] = {
        "chatId": to,
        "caption": caption,
        "session": target_session,
        "url": image_url,
    }
    headers = _build_headers(settings.waha_api_token)
    await _post_with_retry(url, payload, headers)



async def check_health() -> dict[str, Any]:
    settings = get_settings()
    if not settings.waha_base_url:
        return {"status": "error", "detail": "WAHA_BASE_URL not set"}
    
    url = f"{settings.waha_base_url.rstrip('/')}/api/sessions"
    headers = _build_headers(settings.waha_api_token)
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url, headers=headers)
            return {
                "status": "ok" if response.status_code < 400 else "error",
                "status_code": response.status_code,
                "url": url,
                "response": response.json() if response.status_code < 400 else response.text
            }
    except Exception as exc:
        return {"status": "error", "detail": str(exc), "url": url}


async def _post_with_retry(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    client: httpx.AsyncClient | None = None,
) -> None:
    attempts = MAX_ATTEMPTS
    last_exc: Exception | None = None
    
    for attempt in range(1, attempts + 1):
        try:
            if client:
                response = await client.post(url, json=payload, headers=headers, timeout=15)
            else:
                async with httpx.AsyncClient() as http_client:
                    response = await http_client.post(
                        url, json=payload, headers=headers, timeout=15
                    )
            
            if response.status_code < 400:
                logger.info("WAHA call ok url=%s attempt=%s", url, attempt)
                return
            
            # Handle Auth errors specifically
            if response.status_code in (401, 403):
                logger.warning("WAHA Auth Error: status=%s url=%s payload=%s", response.status_code, url, payload)
                return  # Do not raise, just log and exit
                
            logger.warning("WAHA call failed status=%s url=%s payload=%s body=%s", 
                           response.status_code, url, payload, response.text)
            
        except Exception as exc:  # pragma: no cover - external integration
            last_exc = exc
            logger.warning("WAHA call exception attempt %s/%s: %s", attempt, attempts, exc)
            
        if attempt < attempts:
            await asyncio.sleep(RETRY_DELAY_SECONDS)
            
    # If we get here, all attempts failed (except 401/403 which return early)
    raise ProviderError(f"Failed to deliver message via WAHA after {attempts} attempts") from last_exc

