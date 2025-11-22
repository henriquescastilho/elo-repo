import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

async def fetch(query: str) -> List[Dict[str, Any]]:
    """
    Busca matérias no Senado Federal.
    NOTA: Implementação mockada por enquanto para garantir estabilidade, 
    já que a API do Senado requer tratamento complexo de XML/SOAP em alguns endpoints antigos.
    """
    logger.debug("DataHub: Buscando Senado: query=%s", query)
    
    # Simulação de delay ou chamada real futura
    # Em produção, usaríamos https://legis.senado.leg.br/dadosabertos/materia/pesquisa/lista
    
    results = []
    if "saude" in query.lower() or "sus" in query.lower():
        results.append({
            "source": "senado",
            "id": "PL-SENADO-1234",
            "titulo": "Projeto de Lei do Senado sobre Telemedicina",
            "conteudo": "Regulamenta o uso de telemedicina no SUS de forma permanente.",
            "data": "2024",
            "link": "https://www25.senado.leg.br/web/atividade/materias/-/materia/123456"
        })
    
    return results
