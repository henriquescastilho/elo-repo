import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

async def fetch(query: str) -> List[Dict[str, Any]]:
    """
    Busca indicadores na Base dos Dados.
    """
    logger.debug("DataHub: Buscando Base dos Dados: query=%s", query)
    
    # Mock: Em produção usaríamos BigQuery client
    results = []
    if "populacao" in query.lower() or "censo" in query.lower():
        results.append({
            "source": "bd",
            "id": "BD-CENSO-2022",
            "titulo": "Censo Demográfico 2022",
            "conteudo": "Dados preliminares do Censo 2022 indicam crescimento populacional desacelerado.",
            "data": "2022",
            "link": "https://basedosdados.org/dataset/br-ibge-censo-demografico"
        })
    
    return results
