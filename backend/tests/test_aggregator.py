import pytest
from unittest.mock import patch
from backend.app.services.datahub import aggregator

@pytest.mark.anyio
async def test_aggregator_search_all():
    # Mock return values for each service
    mock_camara = [{"source": "camara", "id": "1", "titulo": "PL 1", "conteudo": "Lei", "link": "http", "data": "2024"}]
    mock_senado = [{"source": "senado", "id": "2", "titulo": "PL 2", "conteudo": "Lei", "link": "http", "data": "2024"}]
    mock_qd = [{"source": "qd", "id": "3", "titulo": "DO", "conteudo": "Decreto", "link": "http", "data": "2024"}]
    mock_bd = [{"source": "basedosdados", "id": "4", "titulo": "Dataset", "conteudo": "Dados", "link": "http", "data": "2024"}]
    mock_tse = [{"source": "tse", "id": "5", "titulo": "Cand", "conteudo": "Eleicao", "link": "http", "data": "2024"}]
    mock_datajud = [{"source": "datajud", "id": "6", "titulo": "Proc", "conteudo": "Justica", "link": "http", "data": "2024"}]

    with patch("backend.app.services.datahub.camara_service.fetch", return_value=mock_camara), \
         patch("backend.app.services.datahub.senado_service.fetch", return_value=mock_senado), \
         patch("backend.app.services.datahub.queridodiario_service.fetch", return_value=mock_qd), \
         patch("backend.app.services.datahub.basedosdados_service.fetch", return_value=mock_bd), \
         patch("backend.app.services.datahub.tse_service.fetch", return_value=mock_tse), \
         patch("backend.app.services.datahub.datajud_service.fetch", return_value=mock_datajud):
        
        results = await aggregator.search_all_sources("teste")
        
        # Check if we got results from multiple sources
        sources = {item["source"] for item in results}
        
        assert "camara" in sources
        assert "senado" in sources
        assert "qd" in sources
        assert "basedosdados" in sources
        assert "tse" in sources
        assert "datajud" in sources
        
        # Check structure
        first = results[0]
        assert "id" in first
        assert "title" in first
        assert "summary" in first
