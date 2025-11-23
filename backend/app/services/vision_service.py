import logging
from backend.app.config import get_settings

logger = logging.getLogger(__name__)

async def analyze_image(image_url: str, prompt: str = "Descreva esta imagem com detalhes relevantes para um cidadão.") -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY ausente; ignorando visão.")
        return "Erro: Chave de API não configurada para visão."

    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.warning("SDK OpenAI ausente.")
        return "Erro: SDK OpenAI não instalado."

    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_api_base or "https://api.openai.com/v1",
    )
    
    model = getattr(settings, "vision_model_name", "gpt-4o")

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                }
            ],
            max_tokens=500,
        )
        return response.choices[0].message.content or "Sem descrição."
    except Exception as exc:
        logger.exception("Erro na análise de visão: %s", exc)
        return "Erro ao analisar a imagem."
