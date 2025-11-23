import logging
from typing import List, Dict, Any

import httpx

logger = logging.getLogger(__name__)


async def fetch(query: str) -> List[Dict[str, Any]]:
    """
    Busca em Diários Oficiais via Querido Diário (Open Knowledge Brasil).
    Endpoint: https://queridodiario.ok.org.br/api/v1/publicacoes/
    """
    query_lower = query.lower()
    base_url = "https://queridodiario.ok.org.br"
    endpoint = f"{base_url.rstrip('/')}/api/v1/publicacoes/"
    params = {"querystring": query, "page_size": 5}

    logger.debug("DataHub: Buscando Querido Diário: %s params=%s", endpoint, params)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            payload = response.json()
            items = payload.get("results") or payload.get("data") or []
            results = []
            for item in items:
                results.append(
                    {
                        "source": "qd",
                        "id": str(item.get("id") or item.get("territory_id") or item.get("edition") or ""),
                        "titulo": item.get("title") or item.get("titulo") or "Publicação em Diário Oficial",
                        "conteudo": item.get("content") or item.get("ementa") or item.get("resumo") or "",
                        "data": item.get("date") or item.get("data_publicacao") or item.get("published_at") or "",
                        "link": item.get("url") or item.get("link") or item.get("file_url") or base_url,
                    }
                )
            return [r for r in results if r.get("id")]
    except Exception as exc:
        logger.warning("DataHub: Falha no Querido Diário: %s", exc)
        return []
