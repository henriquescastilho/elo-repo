"""Vision service using GPT-4o multimodal."""

import base64
import logging
from pathlib import Path
from typing import Any, Dict, List

from backend.app.config import Settings, get_settings

logger = logging.getLogger(__name__)
FALLBACK_VISION_MESSAGE = "Não consegui analisar a imagem agora. Pode tentar de novo?"


def _to_image_content(image_url: str) -> Dict[str, Any]:
    if image_url.startswith("http"):
        return {"type": "image_url", "image_url": {"url": image_url}}
    path = Path(image_url)
    if not path.exists():
        logger.warning("Imagem não encontrada em %s", image_url)
        return {"type": "text", "text": "Imagem não encontrada."}
    data = base64.b64encode(path.read_bytes()).decode("utf-8")
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}}


async def _call_vision_openai(image_url: str, user_text: str | None, settings: Settings) -> str:
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY ausente para visão; usando fallback.")
        return FALLBACK_VISION_MESSAGE
    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.warning("SDK OpenAI não está instalado para visão.")
        return FALLBACK_VISION_MESSAGE

    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_api_base or "https://api.openai.com/v1",
    )
    model = getattr(settings, "vision_model_name", None) or "gpt-4o"
    content: List[Dict[str, Any]] = [_to_image_content(image_url)]
    if user_text:
        content.insert(0, {"type": "text", "text": user_text})
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Você descreve imagens em português simples e responde perguntas de forma direta.",
                },
                {
                    "role": "user",
                    "content": content,
                },
            ],
            max_tokens=300,
        )
    except Exception as exc:  # pragma: no cover - external dependency
        logger.exception("OpenAI visão falhou: %s", exc)
        return FALLBACK_VISION_MESSAGE

    if not response.choices:
        return FALLBACK_VISION_MESSAGE
    return response.choices[0].message.content or FALLBACK_VISION_MESSAGE


async def describe_image_and_extract_question(image_url: str, user_text: str | None) -> str:
    """Use GPT-4o multimodal to describe the image and infer the user's question."""
    settings = get_settings()
    logger.info("Describing image via %s for url=%s", settings.vision_provider.lower(), image_url)

    if (settings.vision_provider or "openai").lower() != "openai":
        logger.warning("Visão provider não suportado; usando fallback.")
        return FALLBACK_VISION_MESSAGE

    return await _call_vision_openai(image_url, user_text, settings)
