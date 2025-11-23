import pytest
from unittest.mock import patch
from backend.app.services.datahub import aggregator

@pytest.mark.anyio
async def test_search_legal_sources():
    mock_camara = [{"source": "camara", "id": "1", "titulo": "PL 1", "conteudo": "Lei", "link": "http", "data": "2024"}]
    mock_senado = [{"source": "senado", "id": "2", "titulo": "PL 2", "conteudo": "Lei", "link": "http", "data": "2024"}]
    
    with patch("backend.app.services.datahub.camara_service.fetch", return_value=mock_camara), \
         patch("backend.app.services.datahub.senado_service.fetch", return_value=mock_senado):
        
        results = await aggregator.search_legal_sources("saude")
        
        assert isinstance(results, list)
        assert len(results) == 2
        
        first = results[0]
        assert "id" in first
        assert "title" in first
        assert "summary" in first
        assert "source" in first

@pytest.mark.anyio
async def test_search_all_sources():
    mock_qd = [{"source": "qd", "id": "3", "titulo": "DO", "conteudo": "Decreto", "link": "http", "data": "2024"}]
    
    # We only need to verify that it aggregates correctly, so we can mock just one or all.
    # The aggregator calls all services. We should mock all to avoid network calls.
    with patch("backend.app.services.datahub.camara_service.fetch", return_value=[]), \
         patch("backend.app.services.datahub.senado_service.fetch", return_value=[]), \
         patch("backend.app.services.datahub.queridodiario_service.fetch", return_value=mock_qd), \
         patch("backend.app.services.datahub.basedosdados_service.fetch", return_value=[]), \
         patch("backend.app.services.datahub.tse_service.fetch", return_value=[]), \
         patch("backend.app.services.datahub.datajud_service.fetch", return_value=[]):
        
        results = await aggregator.search_all_sources("transporte")
        
        assert isinstance(results, list)
        found_qd = any(r["source"] == "qd" for r in results)
        assert found_qd
