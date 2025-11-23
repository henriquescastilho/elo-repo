import logging
from typing import List, Dict, Any

import httpx

logger = logging.getLogger(__name__)


async def fetch(query: str) -> List[Dict[str, Any]]:
    """
    Busca datasets públicos na Base dos Dados via API CKAN.
    Endpoint: https://basedosdados.org/api/3/action/package_search
    """
    query.lower()
    url = "https://basedosdados.org/api/3/action/package_search"
    params = {"q": query, "rows": 5}

    logger.debug("DataHub: Buscando Base dos Dados: %s params=%s", url, params)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
            results_raw = payload.get("result", {}).get("results", [])
            results = []
            for item in results_raw:
                # Tenta pegar um link útil (dataset ou primeiro recurso)
                resource_url = ""
                resources = item.get("resources") or []
                if resources:
                    resource_url = resources[0].get("url") or ""

                results.append(
                    {
                        "source": "basedosdados",
                        "id": str(item.get("id") or ""),
                        "titulo": item.get("title") or item.get("name") or "Dataset público",
                        "conteudo": item.get("notes") or item.get("description") or "",
                        "data": item.get("metadata_modified") or item.get("metadata_created") or "",
                        "link": item.get("url") or resource_url or "https://basedosdados.org/",
                    }
                )
            return [r for r in results if r.get("id")]
    except Exception as exc:
        logger.warning("DataHub: Falha na Base dos Dados: %s", exc)
        return []
