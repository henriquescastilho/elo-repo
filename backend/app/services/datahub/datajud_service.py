import logging
import httpx
from typing import List, Dict, Any
import json

logger = logging.getLogger(__name__)

async def fetch(query: str) -> List[Dict[str, Any]]:
    """
    Busca processos na API Pública do DataJud (CNJ).
    Endpoint: https://api-publica.datajud.cnj.jus.br/api_publica_cnj/processo/pesquisa_publica
    
    Nota: A API requer payload específico. Esta implementação tenta uma busca genérica.
    """
    url = "https://api-publica.datajud.cnj.jus.br/api_publica_cnj/processo/pesquisa_publica"
    
    # Payload simplificado para tentativa de busca textual (se suportado)
    # Na prática, o DataJud exige filtros estruturados. 
    # Tentaremos passar a query como filtro de classe ou assunto se possível, 
    # ou apenas logar a tentativa real.
    payload = {
        "query": {
            "match": {
                "conteudo": query
            }
        },
        "size": 5
    }

    logger.debug("DataHub: Buscando DataJud (Real): %s query=%s", url, query)
    
    try:
        # Timeout curto pois APIs públicas podem ser lentas
        async with httpx.AsyncClient(timeout=15) as client:
            # A API pública pode exigir chave em headers em algumas versões.
            # Tentamos sem chave (acesso público) ou com chave de demonstração se houver.
            headers = {
                "Content-Type": "application/json",
                "API-Key": "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==" # Chave pública genérica encontrada em docs antigos ou vazia
            }
            
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            hits = data.get("hits", {}).get("hits", [])
            
            results = []
            for hit in hits:
                source = hit.get("_source", {})
                results.append({
                    "source": "datajud",
                    "id": str(source.get("numeroProcesso") or hit.get("_id")),
                    "titulo": f"Processo {source.get('numeroProcesso')}",
                    "conteudo": source.get("assuntos", [{}])[0].get("nome") or "Sem descrição",
                    "data": source.get("dataAjuizamento") or "",
                    "link": f"https://datajud.cnj.jus.br/" # Link genérico pois o deep link varia
                })
            
            return results

    except Exception as exc:
        # Não retornamos mock! Apenas logamos o erro real.
        logger.warning("DataHub: Falha na API DataJud: %s", exc)
        return []
