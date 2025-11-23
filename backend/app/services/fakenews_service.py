"""Fake news and political misinformation detection service.

This module uses the same LLM stack as the core ELO assistant
to classify political/factual risk and propose a safe answer.
It also leverages the federated DataHub (Câmara, Senado, TSE,
IBGE/Base dos Dados, DataJud, Querido Diário) as grounding.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, TypedDict

from backend.app.config import get_settings
from backend.app.models.schemas import NormalizedMessage
from backend.app.services import llm_service
from backend.app.services.datahub import aggregator

logger = logging.getLogger(__name__)


class FakeNewsResult(TypedDict):
    risk: str  # "baixo" | "medio" | "alto"
    explanation: str
    safe_answer: str
    should_warn: bool


def _default_result() -> FakeNewsResult:
    return FakeNewsResult(
        risk="baixo",
        explanation=(
            "Não identifiquei indícios fortes de desinformação política ou dados "
            "claramente falsos neste texto com base nas fontes consultadas."
        ),
        safe_answer="",
        should_warn=False,
    )


def _build_documents_snippet(documents: List[Dict[str, Any]], limit: int = 8) -> str:
    if not documents:
        return "- Nenhum documento relevante encontrado nas bases públicas consultadas."

    lines: List[str] = []
    for doc in documents[:limit]:
        title = doc.get("title") or doc.get("titulo") or "Documento"
        summary = doc.get("summary") or doc.get("ementa") or ""
        year = doc.get("year") or doc.get("ano") or ""
        source = doc.get("source") or "desconhecida"
        url = doc.get("url") or doc.get("link") or ""
        label_parts = [title]
        if year:
            label_parts.append(str(year))
        label = " – ".join(label_parts)
        line = f"- [{source}] {label}. {summary}"
        if url:
            line += f" (URL: {url})"
        lines.append(line)
    return "\n".join(lines)


def _parse_llm_json(raw: str) -> FakeNewsResult:
    """Best-effort JSON parsing with sane defaults."""
    base = _default_result()
    try:
        data = json.loads(raw)
    except Exception:
        logger.warning("Falha ao fazer parse JSON do verificador de fake news.")
        return base

    risk = str(data.get("risk", base["risk"])).lower().strip()
    if risk not in ("baixo", "medio", "alto"):
        risk = "baixo"

    explanation = str(data.get("explanation") or base["explanation"]).strip()
    safe_answer = str(data.get("safe_answer") or "").strip()
    should_warn = bool(data.get("should_warn")) if risk != "baixo" else False

    return FakeNewsResult(
        risk=risk,
        explanation=explanation or base["explanation"],
        safe_answer=safe_answer,
        should_warn=should_warn,
    )


async def _call_fake_news_llm(text: str, documents: List[Dict[str, Any]]) -> FakeNewsResult:
    """Delegate the actual classification to the main LLM stack."""
    settings = get_settings()

    docs_snippet = _build_documents_snippet(documents)

    system_prompt = (
        "Você é um verificador de fatos do projeto ELO, especializado em política brasileira.\n"
        "Sua função é analisar mensagens recebidas pelo assistente e identificar possíveis "
        "desinformações, boatos virais ou distorções sobre política, eleições, crimes, verbas "
        "públicas e programas sociais.\n\n"
        "REGRAS:\n"
        "- Use sempre que possível as fontes oficiais fornecidas abaixo (Câmara, Senado, TSE, IBGE, "
        "DataJud, Querido Diário, Base dos Dados).\n"
        "- Não invente dados. Se não tiver segurança, considere risco no máximo 'medio'.\n"
        "- Sempre responda EXCLUSIVAMENTE em JSON válido, sem texto extra.\n"
        "- O JSON deve ter exatamente estas chaves: risk, explanation, safe_answer, should_warn.\n"
        "- 'risk' deve ser um destes valores: 'baixo', 'medio' ou 'alto'.\n"
        "- 'safe_answer' deve ser uma explicação em PT-BR simples, corrigindo o conteúdo se "
        "houver erro ou ambiguidade.\n"
        "- 'should_warn' deve ser true se você julgar importante alertar o cidadão com um aviso explícito."
    )

    user_content = (
        "TEXTO DO CIDADÃO:\n"
        f"{text}\n\n"
        "DOCUMENTOS / FONTES OFICIAIS ENCONTRADOS:\n"
        f"{docs_snippet}\n\n"
        "Tarefa: analise o texto acima, compare com os documentos e produza apenas o JSON pedido."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    try:
        raw_answer, ok = await llm_service._call_llm_openai(messages, settings)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - fallback path
        logger.warning("Falha ao chamar LLM para fake news: %s", exc)
        return _default_result()

    if not ok:
        return _default_result()

    return _parse_llm_json(raw_answer)


async def analyze_text(text: str, context: NormalizedMessage | None = None) -> FakeNewsResult:
    """High-level entry point for fake news analysis.

    - Usa DataHub federado como contexto (todas as fontes).
    - Classifica risco de desinformação.
    - Gera uma resposta segura em linguagem simples.
    """
    normalized = (text or "").strip()
    if not normalized:
        return _default_result()

    try:
        documents = await aggregator.search_all_sources(normalized)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Falha ao consultar DataHub no fake news service: %s", exc)
        documents = []

    result = await _call_fake_news_llm(normalized, documents)
    logger.info(
        "Fake news analysis: user_id=%s risk=%s should_warn=%s",
        getattr(context, "user_id", None),
        result["risk"],
        result["should_warn"],
    )
    return result
