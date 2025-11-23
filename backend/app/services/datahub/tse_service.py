import logging
import httpx
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

async def fetch(query: str) -> List[Dict[str, Any]]:
    """
    Busca dados no TSE (DivulgaCandContas).
    Endpoint: https://divulgacandcontas.tse.jus.br/divulga/rest/v1
    
    Foco: Eleições 2024 (Exemplo: São Paulo - 71072)
    """
    # Configuração para Eleição Municipal 2024 (SP como exemplo padrão para busca real)
    # Em produção, precisaríamos resolver o município da query.
    ano = "2024"
    id_eleicao = "2045202024" # ID da eleição 2024
    ue = "71072" # São Paulo
    cargo = "13" # Prefeito
    
    base_url = "https://divulgacandcontas.tse.jus.br/divulga/rest/v1"
    endpoint = f"{base_url}/candidatura/listar/{ano}/{ue}/{id_eleicao}/{cargo}/candidatos"

    logger.debug("DataHub: Buscando TSE (Real): %s query=%s", endpoint, query)
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(endpoint)
            response.raise_for_status()
            
            data = response.json()
            candidatos = data.get("candidatos", [])
            
            results = []
            query_lower = query.lower()
            
            for cand in candidatos:
                nome_urna = cand.get("nomeUrna", "").lower()
                nome_comp = cand.get("nomeCompleto", "").lower()
                
                # Filtro local simples
                if query_lower in nome_urna or query_lower in nome_comp:
                    results.append({
                        "source": "tse",
                        "id": str(cand.get("id")),
                        "titulo": f"Candidato: {cand.get('nomeUrna')} ({cand.get('numero')})",
                        "conteudo": f"Partido: {cand.get('partido', {}).get('sigla')} - {cand.get('descricaoSituacao')}",
                        "data": "2024",
                        "link": f"https://divulgacandcontas.tse.jus.br/divulga/#/candidato/{ano}/{id_eleicao}/{ue}/{cand.get('id')}"
                    })
            
            return results

    except Exception as exc:
        logger.warning("DataHub: Falha na API TSE: %s", exc)
        return []
