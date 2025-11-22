"""LLM orchestration layer."""

import hashlib
import logging
from typing import Any, List, Tuple

from backend.app.config import Settings, get_settings
from backend.app.core.llm import prompt_base
from backend.app.models.schemas import NormalizedMessage
from backend.app.services import cache_service, rag_service

logger = logging.getLogger(__name__)

FALLBACK_LLM_MESSAGE = (
    "Tive um problema para acessar o modelo de IA agora. Tente de novo em alguns instantes."
)


async def _call_llm_openai(system_prompt: str, user_prompt: str, settings: Settings) -> Tuple[str, bool]:
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY ausente; devolvendo fallback.")
        return FALLBACK_LLM_MESSAGE, False
    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.warning("SDK OpenAI não está instalado.")
        return FALLBACK_LLM_MESSAGE, False

    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_api_base or "https://api.openai.com/v1",
    )
    model = getattr(settings, "llm_model_name", None) or "gpt-4o-mini"
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
    except Exception as exc:  # pragma: no cover - external dependency path
        logger.exception("OpenAI chat completion falhou: %s", exc)
        return FALLBACK_LLM_MESSAGE, False

    content = ""
    if response.choices:
        content = response.choices[0].message.content or ""
    if not content:
        logger.warning("OpenAI retornou resposta vazia.")
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
        # Aqui poderíamos processar o conteúdo do arquivo/imagem se já não estiver no texto.
        # Por enquanto, assumimos que o 'context' (NormalizedMessage) traz info suficiente ou o texto já descreve.
        legislative_context = "(Modo Oráculo: Responda com base no arquivo/áudio/imagem enviado pelo usuário)"
    else:
        try:
            documents = await rag_service.search_relevant_documents(normalized_question)
            logger.debug("Retrieved %d documents for grounding", len(documents))
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

    user_prompt = (
        f"Pergunta do usuário: {normalized_question}\n"
        "Contexto federado (resuma em poucas linhas):\n"
        f"{legislative_context or '- Sem contexto externo; responda com orientação geral e clara.'}\n"
        "Responda em português brasileiro simples, frases curtas, e inclua um exemplo prático quando ajudar a entender."
    )

    answer, success = await _call_llm_openai(system_prompt, user_prompt, settings)
    if success:
        await cache_service.set_cached_answer(cache_key, answer)
    return answer
