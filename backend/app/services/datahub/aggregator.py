import asyncio
import logging
from typing import List, Dict, Any

from backend.app.services.datahub import (
    camara_service,
    senado_service,
    queridodiario_service,
    basedosdados_service,
    tse_service,
    datajud_service,
)

logger = logging.getLogger(__name__)


async def _fetch_safe(coroutine, source_name: str) -> List[Dict[str, Any]]:
    try:
        return await coroutine
    except Exception as exc:
        logger.error("Erro na fonte %s: %s", source_name, exc)
        return []


async def search_legal_sources(query: str) -> List[Dict[str, Any]]:
    """
    Busca apenas em fontes legislativas federais (Câmara e Senado).
    """
    logger.info("DataHub Aggregator: Iniciando busca LEGAL para query='%s'", query)
    
    tasks = [
        _fetch_safe(camara_service.fetch(query), "camara"),
        _fetch_safe(senado_service.fetch(query), "senado"),
    ]
    
    results_list = await asyncio.gather(*tasks)
    return _deduplicate_and_normalize(results_list)


import time

async def search_all_sources(query: str) -> List[Dict[str, Any]]:
    """
    Consulta todas as fontes do DataHub em paralelo e agrega os resultados.
    """
    start_time = time.perf_counter()
    logger.info("DataHub Aggregator: Iniciando busca FEDERADA (ALL) para query='%s'", query)
    
    tasks = [
        _fetch_safe(camara_service.fetch(query), "camara"),
        _fetch_safe(senado_service.fetch(query), "senado"),
        _fetch_safe(queridodiario_service.fetch(query), "queridodiario"),
        _fetch_safe(basedosdados_service.fetch(query), "basedosdados"),
        _fetch_safe(tse_service.fetch(query), "tse"),
        _fetch_safe(datajud_service.fetch(query), "datajud"),
    ]
    
    results_list = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start_time
    logger.info("DataHub Aggregator: Busca FEDERADA concluída em %.2fs", elapsed)
    
    return _deduplicate_and_normalize(results_list)


def _deduplicate_and_normalize(results_list: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    aggregated: List[Dict[str, Any]] = []
    for result in results_list:
        if result:
            aggregated.extend(result)
            
    # Deduplicação básica por ID
    seen_ids = set()
    unique_results = []
    for item in aggregated:
        doc_id = item.get("id")
        if doc_id and doc_id not in seen_ids:
            seen_ids.add(doc_id)
            # Normalização final (garantir campos)
            normalized = {
                "id": doc_id,
                "titulo": item.get("titulo") or item.get("title") or "Sem título",
                "title": item.get("title") or item.get("titulo") or "Sem título",
                "ementa": item.get("conteudo") or item.get("ementa") or item.get("summary") or "",
                "summary": item.get("summary") or item.get("conteudo") or item.get("ementa") or "",
                "ano": item.get("data") or item.get("ano"),
                "source": item.get("source") or "unknown",
                "link": item.get("link") or item.get("url") or "",
                "raw_metadata": item,
            }
            unique_results.append(normalized)
            
    logger.info("DataHub Aggregator: Encontrados %d documentos únicos.", len(unique_results))
    return unique_results
