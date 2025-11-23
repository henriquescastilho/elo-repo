import base64
import logging
from typing import Optional

from backend.app.config import get_settings

logger = logging.getLogger(__name__)


async def analyze_image(
    image_bytes: Optional[bytes] = None,
    image_url: Optional[str] = None,
    prompt: str = (
        "Descreva tecnicamente o conteúdo da imagem (documentos, boletos, cartas, avisos, "
        "prints de tela etc.). Foque em informações objetivas: remetente, datas, valores, "
        "títulos, campos principais e possíveis alertas de golpe ou cobrança."
    ),
) -> str:
    """
    Análise de imagem usando Vision (Azure ou OpenAI), com suporte a URL ou bytes.
    Retorna um texto descritivo e técnico, adequado para o Modo Oráculo.
    """
    settings = get_settings()

    provider = (getattr(settings, "vision_provider", None) or settings.llm_provider or "openai").lower()

    if provider == "azure":
        if not settings.azure_openai_api_key or not settings.azure_openai_endpoint:
            logger.warning("Azure OpenAI config missing for Vision.")
            return "Erro: Configuração Azure ausente para visão."
        try:
            from openai import AsyncAzureOpenAI

            client = AsyncAzureOpenAI(
                api_key=settings.azure_openai_api_key,
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
            )
            model = settings.azure_deployment_name or "gpt-4o-mini"
            temperature = None
        except ImportError:
            logger.warning("SDK OpenAI (Azure) ausente.")
            return "Erro: SDK OpenAI não instalado para visão."
    else:
        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY ausente; ignorando visão.")
            return "Erro: Chave de API não configurada para visão."
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_api_base or "https://api.openai.com/v1",
            )
            model = getattr(settings, "vision_model_name", None) or "gpt-4o-mini"
            temperature = 0.2
        except ImportError:
            logger.warning("SDK OpenAI ausente.")
            return "Erro: SDK OpenAI não instalado."

    if not image_url and not image_bytes:
        return "Erro: Nenhuma imagem fornecida para análise."

    if not image_url and image_bytes:
        try:
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            image_url = f"data:image/jpeg;base64,{b64_image}"
        except Exception as exc:
            logger.exception("Falha ao converter bytes de imagem para base64: %s", exc)
            return "Erro ao preparar a imagem para análise."

    try:
        create_kwargs = {
            "model": model,
            "messages": [
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
            "max_tokens": 700,
        }
        if temperature is not None:
            create_kwargs["temperature"] = temperature

        response = await client.chat.completions.create(**create_kwargs)
        return response.choices[0].message.content or "Sem descrição."
    except Exception as exc:
        logger.exception("Erro na análise de visão: %s", exc)
        return "Erro ao analisar a imagem."
