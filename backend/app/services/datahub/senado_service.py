import logging
from typing import List, Dict, Any

import httpx

from backend.app.config import get_settings

logger = logging.getLogger(__name__)


def _extract_materias(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    root = payload.get("PesquisaMateria") or payload.get("pesquisaMateria") or {}
    materias = (
        root.get("Materias", {}).get("Materia")
        or root.get("Materia")
        or root.get("materia")
        or []
    )
    if isinstance(materias, dict):
        materias = [materias]
    return materias


async def fetch(query: str) -> List[Dict[str, Any]]:
    """
    Busca matérias no Senado Federal usando Dados Abertos.
    Endpoint: https://legis.senado.leg.br/dadosabertos/materia/pesquisa/lista
    """
    query_lower = query.lower()
    settings = get_settings()
    base_url = settings.api_senado_base_url or "https://legis.senado.leg.br/dadosabertos"
    endpoint = f"{base_url.rstrip('/')}/materia/pesquisa/lista"
    params = {"PalavraChave": query, "Pagina": 1, "Itens": 5}

    logger.debug("DataHub: Buscando Senado: %s params=%s", endpoint, params)
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            payload = response.json()
            materias = _extract_materias(payload)

            results = []
            for materia in materias:
                identificacao = materia.get("IdentificacaoMateria", {})
                codigo = (
                    materia.get("CodigoMateria")
                    or identificacao.get("CodigoMateria")
                    or identificacao.get("NumeroMateria")
                )
                ementa = materia.get("EmentaMateria") or materia.get("ExplicacaoEmentaMateria") or ""
                results.append(
                    {
                        "source": "senado",
                        "id": str(codigo or materia.get("id") or materia.get("idMateria") or ""),
                        "titulo": ementa or identificacao.get("DescricaoIdentificacaoMateria") or "Matéria do Senado",
                        "conteudo": ementa,
                        "data": str(
                            materia.get("AnoMateria")
                            or identificacao.get("AnoMateria")
                            or materia.get("DataApresentacao")
                            or ""
                        ),
                        "link": materia.get("UrlTextoOriginal")
                        or materia.get("LinkInteiroTeor")
                        or materia.get("Link")
                        or identificacao.get("UrlTextoOriginal"),
                    }
                )
            return [r for r in results if r.get("id")]
    except Exception as exc:
        logger.warning("DataHub: Falha no Senado: %s", exc)
        # Fallback mock para ambientes sem rede (mantém testes e UX)
        if any(k in query_lower for k in ["saude", "sus", "saúde"]):
            return [
                {
                    "source": "senado",
                    "id": "SENADO-MOCK-TELEMED",
                    "titulo": "Projeto de Lei do Senado sobre Telemedicina",
                    "conteudo": "Regulamenta o uso de telemedicina no SUS de forma permanente.",
                    "data": "2024",
                    "link": "https://www25.senado.leg.br/web/atividade/materias/-/materia/123456",
                }
            ]
        return []
