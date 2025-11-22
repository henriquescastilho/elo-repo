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

async def search_all_sources(query: str) -> List[Dict[str, Any]]:
    """
    Consulta todas as fontes do DataHub em paralelo e agrega os resultados.
    """
    logger.info("DataHub Aggregator: Iniciando busca federada para query='%s'", query)
    
    # Lista de corrotinas para execução paralela
    tasks = [
        camara_service.fetch(query),
        senado_service.fetch(query),
        queridodiario_service.fetch(query),
        basedosdados_service.fetch(query),
        tse_service.fetch(query),
        datajud_service.fetch(query),
    ]
    
    # Executa todas e aguarda resultados (retorna lista de listas)
    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    
    aggregated: List[Dict[str, Any]] = []
    
    for i, result in enumerate(results_list):
        if isinstance(result, Exception):
            logger.error("Erro na fonte %d: %s", i, result)
            continue
        if result:
            aggregated.extend(result)
            
    # Deduplicação básica por ID (caso haja overlap, embora fontes sejam distintas)
    seen_ids = set()
    unique_results = []
    for item in aggregated:
        doc_id = item.get("id")
        if doc_id and doc_id not in seen_ids:
            seen_ids.add(doc_id)
            unique_results.append(item)
            
    logger.info("DataHub Aggregator: Encontrados %d documentos únicos.", len(unique_results))
    return unique_results
