"""Retrieval augmented generation helpers with optional LangChain support."""

import os
from typing import Any, Dict, List

import httpx

from backend.app.config import get_settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

LANGCHAIN_ENABLED = os.getenv("LANGCHAIN_ENABLED", "false").lower() == "true"
FAISS = None
OpenAIEmbeddings = None
Document = None

if LANGCHAIN_ENABLED:
    try:  # pragma: no cover - optional dependency
        from langchain_community.vectorstores import FAISS as _FAISS
        from langchain_core.documents import Document as _Document
        from langchain_openai import OpenAIEmbeddings as _OpenAIEmbeddings

        FAISS = _FAISS
        Document = _Document
        OpenAIEmbeddings = _OpenAIEmbeddings
    except ImportError:  # pragma: no cover - optional dependency
        logger.warning(
            "LANGCHAIN_ENABLED=true mas dependências não estão instaladas. Voltando ao modo básico."
        )
        LANGCHAIN_ENABLED = False

MOCK_LEGAL_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "id": "MOCK-001",
        "titulo": "Direitos básicos do cidadão",
        "ementa": "Todo cidadão tem direito a atendimento e informação clara nos órgãos públicos.",
        "ano": 2024,
        "source": "mock",
    },
    {
        "id": "MOCK-002",
        "titulo": "Acesso à informação",
        "ementa": "Lei de Acesso à Informação garante transparência e resposta ágil do governo.",
        "ano": 2023,
        "source": "mock",
    },
    {
        "id": "MOCK-003",
        "titulo": "Participação social",
        "ementa": "Cidadãos podem propor ideias legislativas e participar de audiências públicas.",
        "ano": 2022,
        "source": "mock",
    },
]


async def _search_mock(query: str) -> List[Dict[str, Any]]:
    """Return mock documents filtered by the query."""
    if not query:
        return MOCK_LEGAL_DOCUMENTS
    query_lower = query.lower()
    filtered = [doc for doc in MOCK_LEGAL_DOCUMENTS if query_lower in doc["ementa"].lower()]
    return filtered or MOCK_LEGAL_DOCUMENTS


async def _search_api_camara(query: str) -> List[Dict[str, Any]]:
    """Search propositions at Câmara dos Deputados Open Data API."""
    settings = get_settings()
    base_url = settings.api_camara_base_url or "https://dadosabertos.camara.leg.br/api/v2"
    endpoint = f"{base_url.rstrip('/')}/proposicoes"
    params = {
        "keywords": query,
        "itens": 5,
        "ordem": "DESC",
        "ordenarPor": "id",
    }

    logger.debug("Calling Câmara API: %s params=%s", endpoint, params)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(endpoint, params=params)
            status_code = response.status_code
            logger.debug("Câmara API status=%s", status_code)
            response.raise_for_status()
    except Exception as exc:  # pragma: no cover - network issues
        logger.warning("Falha ao consultar API da Câmara: %s", exc)
        return []

    payload = response.json()
    items = payload.get("dados", [])
    logger.debug("Câmara API returned %d items", len(items))
    results: List[Dict[str, Any]] = []
    for item in items:
        results.append(
            {
                "id": str(item.get("id")),
                "titulo": item.get("ementa") or item.get("siglaTipo") or "Proposição",
                "ementa": item.get("ementa") or "",
                "ano": item.get("ano"),
                "source": "camara",
            }
        )
    return results


def _build_langchain_retriever(docs: List[Dict[str, Any]]):
    if not (LANGCHAIN_ENABLED and FAISS and OpenAIEmbeddings and Document):
        raise RuntimeError("LangChain não está totalmente disponível.")
    if not docs:
        raise ValueError("Sem documentos para indexar.")

    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY não configurada para embeddings.")

    documents = []
    for doc in docs:
        page_content = doc.get("ementa") or doc.get("titulo") or "Documento"
        metadata = {
            "id": doc.get("id"),
            "titulo": doc.get("titulo"),
            "ano": doc.get("ano"),
            "source": doc.get("source"),
            "ementa": doc.get("ementa"),
        }
        documents.append(Document(page_content=page_content, metadata=metadata))

    embed_kwargs = {
        "openai_api_key": settings.openai_api_key,
        "model": getattr(settings, "embedding_model_name", None) or "text-embedding-3-small",
    }
    if settings.openai_api_base:
        embed_kwargs["openai_api_base"] = settings.openai_api_base

    embeddings = OpenAIEmbeddings(**embed_kwargs)
    vectorstore = FAISS.from_documents(documents, embeddings)
    return vectorstore.as_retriever(search_kwargs={"k": 3})


async def search_relevant_documents(query: str, mode: str | None = None) -> List[Dict[str, Any]]:
    settings = get_settings()
    mode = (mode or settings.legal_data_source_mode).lower()

    if mode == "mock":
        logger.info("RAG using mock mode")
        docs = await _search_mock(query)
    elif mode == "api":
        logger.info("RAG using API mode (Câmara only)")
        docs = await _search_api_camara(query)
    elif mode == "legal_only":
        logger.info("RAG using DataHub Aggregator (Legal Sources)")
        from backend.app.services.datahub import aggregator
        docs = await aggregator.search_legal_sources(query)
    elif mode == "all":
        logger.info("RAG using DataHub Aggregator (All Sources)")
        from backend.app.services.datahub import aggregator
        docs = await aggregator.search_all_sources(query)
    else:
        logger.warning("LEGAL_DATA_SOURCE_MODE '%s' desconhecido. Usando mock.", mode)
        docs = await _search_mock(query)

    if not docs:
        docs = await _search_mock(query)

    if LANGCHAIN_ENABLED and docs:
        try:
            retriever = _build_langchain_retriever(docs)
            lc_results = retriever.get_relevant_documents(query)
            normalized: List[Dict[str, Any]] = []
            for doc in lc_results:
                metadata = doc.metadata or {}
                normalized.append(
                    {
                        "id": metadata.get("id"),
                        "titulo": metadata.get("titulo") or metadata.get("id") or "Documento",
                        "ementa": doc.page_content,
                        "ano": metadata.get("ano"),
                        "source": metadata.get("source", "camara"),
                    }
                )
            if normalized:
                return normalized
        except Exception as exc:  # pragma: no cover - optional path
            logger.warning("Falha ao usar LangChain. Voltando para resultado padrão: %s", exc)

    return docs
