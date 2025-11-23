import logging
import os
from backend.app.config import get_settings

logger = logging.getLogger(__name__)

async def transcribe_audio(audio_path: str) -> str:
    settings = get_settings()
    provider = (settings.stt_provider or "openai").lower()
    client = None
    model = getattr(settings, "stt_model_name", "whisper-1")

    if provider == "azure":
        if not settings.azure_openai_api_key or not settings.azure_openai_endpoint:
            logger.warning("Azure OpenAI config missing for STT.")
            return "Erro: Configuração Azure ausente."
        try:
            from openai import AsyncAzureOpenAI
            client = AsyncAzureOpenAI(
                api_key=settings.azure_openai_api_key,
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
            )
            model = (
                settings.azure_stt_deployment_name
                or getattr(settings, "stt_model_name", None)
                or settings.azure_deployment_name
                or "whisper-1"
            )
        except ImportError:
            logger.warning("OpenAI SDK not installed.")
            return "Erro: SDK OpenAI não instalado."
    else:
        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY ausente; ignorando STT.")
            return "Erro: Chave de API não configurada para áudio."
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_api_base or "https://api.openai.com/v1",
            )
        except ImportError:
            logger.warning("SDK OpenAI ausente.")
            return "Erro: SDK OpenAI não instalado."

    if not os.path.exists(audio_path):
        return "Erro: Arquivo de áudio não encontrado."

    try:
        with open(audio_path, "rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                model=model,
                file=audio_file,
            )
        return transcript.text or "Sem transcrição."
    except Exception as exc:
        logger.exception("Erro na transcrição de áudio: %s", exc)
        return "Erro ao transcrever áudio."
