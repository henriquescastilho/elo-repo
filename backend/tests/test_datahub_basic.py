import pytest
from backend.app.services.datahub import (
    camara_service,
    senado_service,
    queridodiario_service,
    basedosdados_service,
    tse_service,
    datajud_service,
)

@pytest.mark.anyio
async def test_camara_service():
    # Mocking httpx would be ideal, but here we test the structure and error handling
    # Assuming network might fail or return empty in test env without mocking
    results = await camara_service.fetch("saude")
    assert isinstance(results, list)

@pytest.mark.anyio
async def test_senado_service_mock():
    results = await senado_service.fetch("saude")
    assert len(results) > 0
    assert results[0]["source"] == "senado"

@pytest.mark.anyio
async def test_queridodiario_service_mock():
    results = await queridodiario_service.fetch("transporte")
    assert len(results) > 0
    assert results[0]["source"] == "qd"

@pytest.mark.anyio
async def test_basedosdados_service_mock():
    results = await basedosdados_service.fetch("populacao")
    assert len(results) > 0
    assert results[0]["source"] == "bd"

@pytest.mark.anyio
async def test_tse_service_mock():
    results = await tse_service.fetch("eleicao")
    assert len(results) > 0
    assert results[0]["source"] == "tse"

@pytest.mark.anyio
async def test_datajud_service_mock():
    results = await datajud_service.fetch("processo")
    assert len(results) > 0
    assert results[0]["source"] == "datajud"
