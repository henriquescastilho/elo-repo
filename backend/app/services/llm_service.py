"""LLM orchestration layer."""

import hashlib
import logging
from typing import Any, List, Tuple

from backend.app.config import Settings, get_settings
from backend.app.core.llm import prompt_base
from backend.app.models.schemas import NormalizedMessage
from backend.app.services import cache_service, rag_service
import io
import httpx
import pypdf

logger = logging.getLogger(__name__)

FALLBACK_LLM_MESSAGE = (
    "Tive um problema para acessar o modelo de IA agora. Tente de novo em alguns instantes."
)


from tenacity import retry, stop_after_attempt, wait_exponential, RetryCallState

def return_fallback_on_failure(retry_state: RetryCallState) -> Tuple[str, bool]:
    logger.error("Tenacity retries exhausted: %s", retry_state.outcome.exception())
    return FALLBACK_LLM_MESSAGE, False

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
    retry_error_callback=return_fallback_on_failure
)
async def _call_llm_openai(messages: List[dict[str, Any]], settings: Settings) -> Tuple[str, bool]:
    provider = (settings.llm_provider or "openai").lower()
    client = None
    model = None

    if provider == "azure":
        if not settings.azure_openai_api_key or not settings.azure_openai_endpoint:
            logger.warning("Azure OpenAI config missing (key/endpoint).")
            return FALLBACK_LLM_MESSAGE, False
        try:
            from openai import AsyncAzureOpenAI
            client = AsyncAzureOpenAI(
                api_key=settings.azure_openai_api_key,
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
            )
            model = settings.azure_deployment_name or "gpt-4o"
            temperature = None  # alguns modelos Azure não aceitam temperatura customizada
        except ImportError:
            logger.warning("OpenAI SDK não está instalado.")
            return FALLBACK_LLM_MESSAGE, False

    else:  # Default to OpenAI
        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY ausente; devolvendo fallback.")
            return FALLBACK_LLM_MESSAGE, False
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_api_base or "https://api.openai.com/v1",
            )
            model = getattr(settings, "llm_model_name", None) or "gpt-4o-mini"
            temperature = 0.3
        except ImportError:
            logger.warning("SDK OpenAI não está instalado.")
            return FALLBACK_LLM_MESSAGE, False

    try:
        create_kwargs = {"model": model, "messages": messages}
        if temperature is not None:
            create_kwargs["temperature"] = temperature

        response = await client.chat.completions.create(**create_kwargs)
    except Exception as exc:  # pragma: no cover - external dependency path
        logger.exception("%s chat completion falhou: %s", provider.upper(), exc)
        # Tenacity will catch this if we re-raise, but the original code returned a fallback.
        # To make tenacity work, we MUST raise the exception so it can retry.
        # After retries are exhausted, tenacity will raise the exception.
        # We need to handle the final failure outside or let it bubble up.
        # However, the signature expects (str, bool).
        # Let's raise here to trigger retry, and catch in the caller?
        # Or better: The original code swallowed exceptions.
        # If I want retry, I must raise.
        raise exc

    content = ""
    if response.choices:
        content = response.choices[0].message.content or ""
    if not content:
        logger.warning("%s retornou resposta vazia.", provider.upper())
        return FALLBACK_LLM_MESSAGE, False
    return content, True


def _normalize_user_text(text: str) -> str:
    normalized = (text or "").strip()
    return " ".join(normalized.split())


def _shorten_ementa(text: str, max_length: int = 240) -> str:
    simplified = " ".join((text or "").split())
    if len(simplified) <= max_length:
        return simplified
    shortened = simplified[:max_length].rsplit(" ", 1)[0]
    return f"{shortened}..."


def _build_legislative_context(documents: List[dict[str, Any]], limit: int = 5) -> str:
    if not documents:
        return ""

    lines = []
    for doc in documents[:limit]:
        doc_id = doc.get("id") or "Documento"
        title = doc.get("titulo") or doc_id
        year = doc.get("ano")
        summary = _shorten_ementa(doc.get("ementa") or doc.get("descricao") or "")
        year_label = f" ({year})" if year else ""
        lines.append(f"- {doc_id}{year_label}: {title}. {summary}")
    return "\n".join(lines)


async def _get_conversation_history(user_id: str, limit: int = 3) -> str:
    state = await cache_service.get_user_state(user_id)
    if not state:
        return ""
    history = state.get("history", [])
    if not history:
        return ""
    
    # Format last N messages
    formatted = []
    for msg in history[-limit:]:
        role = "Usuário" if msg["role"] == "user" else "Bot"
        formatted.append(f"{role}: {msg['content']}")
    return "\n".join(formatted)


async def _update_conversation_history(user_id: str, user_text: str, bot_text: str) -> None:
    state = await cache_service.get_user_state(user_id) or {}
    history = state.get("history", [])
    
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": bot_text})
    
    # Keep only last 10 turns to save space
    if len(history) > 20:
        history = history[-20:]
        
    state["history"] = history
    await cache_service.set_user_state(user_id, state)


def _build_oracle_context_block(context: Any) -> str:
    """
    Constrói bloco de contexto específico do Modo Oráculo a partir de um OracleContext,
    se fornecido, ou de um NormalizedMessage simples.
    """
    contexto = getattr(context, "contexto_oraculo", None)
    if isinstance(contexto, dict):
        tipo = contexto.get("tipo_arquivo") or "desconhecido"
        meta = contexto.get("metadados") or {}
        texto = (contexto.get("texto_extraido") or "").strip()
        tamanho = len(texto)
        preview = texto[:1000]

        logger.info(
            "[ORACULO] tipo=%s tamanho=%d metadados=%s",
            tipo,
            tamanho,
            {k: meta[k] for k in list(meta.keys())[:10]},
        )

        return (
            "### CONTEXTO DO DOCUMENTO ENVIADO PELO USUÁRIO (MODO ORÁCULO)\n"
            f"- Tipo de conteúdo: {tipo}\n"
            f"- Metadados principais: {meta}\n"
            f"- Tamanho aproximado do texto extraído: {tamanho} caracteres\n\n"
            "Trecho inicial do conteúdo extraído (use apenas como base factual, "
            "sem inventar informações que não estejam aqui):\n"
            f"{preview}\n"
        )

    # Fallback simples se não houver contexto estruturado.
    return (
        "(Modo Oráculo) Explique apenas o conteúdo concreto do arquivo, "
        "imagem, áudio ou link enviado. Não dê conselhos emocionais, "
        "não faça julgamentos e não extrapole além do que está no material."
    )


async def answer_user_question(
    user_text: str,
    context: NormalizedMessage | Any = None,
    flow: str | None = None,
    bot_name: str | None = None,
) -> str:
    settings = get_settings()
    normalized_question = _normalize_user_text(user_text)
    user_id = getattr(context, "user_id", None) or "anonymous"
    flow_key = (flow or "elo").lower()
    cache_key = hashlib.sha256(f"{user_id}:{flow_key}:{normalized_question}".encode()).hexdigest()
    cached = await cache_service.get_cached_answer(cache_key)
    if cached:
        logger.info("Cache hit for user=%s", user_id)
        return cached

    documents: List[dict[str, Any]] = []
    legislative_context = ""

    # Se for Oráculo, pulamos o RAG legislativo e focamos no contexto da mensagem (media, arquivos)
    if flow_key == "oraculo":
        logger.info("Fluxo Oráculo: pulando RAG legislativo.")
        legislative_context = _build_oracle_context_block(context)
    else:
        # Define RAG mode based on flow
        # VOTOS: usa apenas fontes legislativas (Câmara + Senado).
        # ELO: usa RAG legal quando o texto indicar termos jurídicos/benefícios.
        rag_mode = "legal_only" if flow_key == "votos" else "mock"

        if flow_key == "elo":
            # Simple heuristic: if query has "lei", "direito", "beneficio", use legal search
            if any(k in normalized_question for k in ["lei", "direito", "beneficio", "auxilio"]):
                rag_mode = "legal_only"
            else:
                rag_mode = "mock"

        try:
            documents = await rag_service.search_relevant_documents(normalized_question, mode=rag_mode)
            logger.debug("Retrieved %d documents for grounding (mode=%s)", len(documents), rag_mode)
        except Exception:
            logger.exception("Falha ao buscar documentos para grounding")
        
        legislative_context = _build_legislative_context(documents)

    flow_instructions = prompt_base.FLOW_INSTRUCTIONS.get(flow_key, prompt_base.FLOW_INSTRUCTIONS["elo"])
    system_name = bot_name or "ELO – Assistente Cidadão"
    
    # Montagem do System Prompt
    system_prompt = (
        f"{prompt_base.BASE_SYSTEM_PROMPT}\n"
        f"Bot: {system_name}\n"
        f"{flow_instructions}\n"
    )

    # Se NÃO for Oráculo, reforçamos o uso dos documentos legislativos
    if flow_key != "oraculo":
        system_prompt += (
            "Use os documentos reais abaixo, vindos de fontes públicas brasileiras (Câmara, Senado, Diários, etc.), "
            "como base da sua resposta. Explique em linguagem simples o que eles significam para a vida do cidadão."
        )

    # Recuperar histórico
    history_text = await _get_conversation_history(user_id)
    
    user_prompt = (
        f"Histórico da conversa:\n{history_text}\n\n"
        f"Pergunta atual do usuário: {normalized_question}\n"
        f"Contexto de Apoio:\n"
        f"{legislative_context or '- Sem contexto externo; responda com orientação geral e clara.'}\n"
        "Responda em português brasileiro simples, frases curtas, e inclua um exemplo prático quando ajudar a entender."
    )

    # Construct messages list
    messages = [
        {"role": "system", "content": system_prompt},
    ]

    # Vision support
    if context and getattr(context, "media_url", None):
        msg_type = getattr(context, "type", "")
        if msg_type == "image":
            logger.info("Incorporating image into LLM prompt: %s", context.media_url)
            user_content = [
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {"url": context.media_url}},
            ]
            messages.append({"role": "user", "content": user_content})
        elif msg_type == "file":
            logger.info("Incorporating file info into LLM prompt: %s", context.media_url)
            
            # Try to download and extract text if it's a PDF
            extracted_text = ""
            if context.media_url and context.media_url.lower().endswith(".pdf"):
                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(context.media_url)
                        if resp.status_code == 200:
                            pdf_file = io.BytesIO(resp.content)
                            reader = pypdf.PdfReader(pdf_file)
                            text_parts = []
                            for page in reader.pages:
                                text_parts.append(page.extract_text())
                            extracted_text = "\n".join(text_parts)
                            logger.info("Extracted %d chars from PDF", len(extracted_text))
                except Exception as exc:
                    logger.warning("Failed to extract PDF text: %s", exc)

            if extracted_text:
                file_prompt = (
                    f"{user_prompt}\n\n"
                    f"[SISTEMA: O usuário enviou um arquivo PDF. Conteúdo extraído abaixo:]\n"
                    f"--- INÍCIO DO ARQUIVO ---\n{extracted_text[:20000]}\n--- FIM DO ARQUIVO ---\n"
                    "Analise o conteúdo acima para responder."
                )
            else:
                file_prompt = (
                    f"{user_prompt}\n\n"
                    f"[SISTEMA: O usuário enviou um arquivo/documento. URL: {context.media_url}. "
                    "Se for um PDF ou documento que você não consegue ler diretamente, avise o usuário que recebeu "
                    "e pergunte do que se trata, ou peça para ele mandar uma foto se for curto.]"
                )
            messages.append({"role": "user", "content": file_prompt})
        else:
            messages.append({"role": "user", "content": user_prompt})
    else:
        messages.append({"role": "user", "content": user_prompt})

    if flow_key == "oraculo":
        logger.info("[ORACULO] enviado ao modelo provider=%s", (settings.llm_provider or "openai").lower())

    answer, success = await _call_llm_openai(messages, settings)
    if success:
        await cache_service.set_cached_answer(cache_key, answer)
        await _update_conversation_history(user_id, normalized_question, answer)
    return answer
