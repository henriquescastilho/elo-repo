import logging
import httpx
from typing import List, Dict, Any
from backend.app.config import get_settings

logger = logging.getLogger(__name__)

async def fetch(query: str) -> List[Dict[str, Any]]:
    """
    Busca proposições na API da Câmara dos Deputados.
    """
    settings = get_settings()
    base_url = settings.api_camara_base_url or "https://dadosabertos.camara.leg.br/api/v2"
    endpoint = f"{base_url.rstrip('/')}/proposicoes"
    params = {
        "keywords": query,
        "itens": 5,
        "ordem": "DESC",
        "ordenarPor": "id",
    }

    logger.debug("DataHub: Buscando Câmara: %s params=%s", endpoint, params)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            payload = response.json()
            items = payload.get("dados", [])
            
            results = []
            for item in items:
                results.append({
                    "source": "camara",
                    "id": str(item.get("id")),
                    "titulo": item.get("ementa") or item.get("siglaTipo") or "Proposição",
                    "conteudo": item.get("ementa") or "",
                    "data": str(item.get("ano")),
                    "link": item.get("uri")
                })
            return results
    except Exception as exc:
        logger.warning("DataHub: Falha na Câmara: %s", exc)
        return []
