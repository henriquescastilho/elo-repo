import pytest
from unittest.mock import MagicMock, patch
from backend.app.services.datahub import (
    camara_service,
    senado_service,
    queridodiario_service,
    basedosdados_service,
    tse_service,
    datajud_service,
)

# Helper to create a mock response
def mock_response(json_data, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp

@pytest.mark.anyio
async def test_camara_service():
    with patch("httpx.AsyncClient.get", return_value=mock_response({"dados": [{"id": 1, "ementa": "Teste"}]})) as mock_get:
        results = await camara_service.fetch("saude")
        assert len(results) > 0
        assert results[0]["source"] == "camara"

@pytest.mark.anyio
async def test_senado_service():
    mock_data = {"PesquisaMateria": {"Materias": {"Materia": [{"IdentificacaoMateria": {"CodigoMateria": "123"}, "EmentaMateria": "Teste Senado"}]}}}
    with patch("httpx.AsyncClient.get", return_value=mock_response(mock_data)) as mock_get:
        results = await senado_service.fetch("saude")
        assert len(results) > 0
        assert results[0]["source"] == "senado"

@pytest.mark.anyio
async def test_queridodiario_service():
    mock_data = {"gazettes": [{"date": "2024-01-01", "url": "http://test", "territory_id": "1", "excerpt": "Teste"}]}
    # Note: The service expects 'results' or 'data' or 'gazettes' depending on version. 
    # Checking code: items = payload.get("results") or payload.get("data") or []
    # Wait, my code uses 'results' or 'data'. 
    mock_data_v1 = {"results": [{"date": "2024-01-01", "url": "http://test", "territory_id": "1", "excerpt": "Teste"}]}
    
    with patch("httpx.AsyncClient.get", return_value=mock_response(mock_data_v1)) as mock_get:
        results = await queridodiario_service.fetch("transporte")
        assert len(results) > 0
        assert results[0]["source"] == "qd"

@pytest.mark.anyio
async def test_basedosdados_service():
    mock_data = {"result": {"results": [{"id": "1", "title": "Teste BD", "resources": [{"url": "http://test"}]}]}}
    with patch("httpx.AsyncClient.get", return_value=mock_response(mock_data)) as mock_get:
        results = await basedosdados_service.fetch("populacao")
        assert len(results) > 0
        assert results[0]["source"] == "basedosdados"

@pytest.mark.anyio
async def test_tse_service():
    mock_data = {"candidatos": [{"id": 1, "nomeUrna": "Teste", "nomeCompleto": "Teste Silva", "numero": 12, "partido": {"sigla": "TST"}}]}
    with patch("httpx.AsyncClient.get", return_value=mock_response(mock_data)) as mock_get:
        results = await tse_service.fetch("Teste")
        assert len(results) > 0
        assert results[0]["source"] == "tse"

@pytest.mark.anyio
async def test_datajud_service():
    mock_data = {"hits": {"hits": [{"_source": {"numeroProcesso": "123", "assuntos": [{"nome": "Teste"}]}}]}}
    with patch("httpx.AsyncClient.post", return_value=mock_response(mock_data)) as mock_post:
        results = await datajud_service.fetch("processo")
        assert len(results) > 0
        assert results[0]["source"] == "datajud"
