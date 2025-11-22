import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

async def fetch(query: str) -> List[Dict[str, Any]]:
    """
    Busca dados eleitorais no TSE.
    """
    logger.debug("DataHub: Buscando TSE: query=%s", query)
    
    # Mock
    results = []
    if "eleicao" in query.lower() or "urna" in query.lower():
        results.append({
            "source": "tse",
            "id": "TSE-2024-RES",
            "titulo": "Calendário Eleitoral 2024",
            "conteudo": "Resolução TSE nº 23.738/2024 define datas das eleições municipais.",
            "data": "2024",
            "link": "https://www.tse.jus.br/"
        })
    
    return results
