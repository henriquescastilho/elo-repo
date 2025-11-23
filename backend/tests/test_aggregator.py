import pytest
from backend.app.services.datahub import aggregator

@pytest.mark.anyio
async def test_aggregator_search_all():
    # Test aggregation of all mocks
    results = await aggregator.search_all_sources("saude transporte populacao eleicao processo")
    
    # Check if we got results from multiple sources
    sources = {item["source"] for item in results}
    
    # We expect at least the mocked ones to return something
    assert "senado" in sources
    assert "qd" in sources
    assert "bd" in sources
    assert "tse" in sources
    assert "datajud" in sources
    
    # Check structure
    first = results[0]
    assert "id" in first
    assert "title" in first
    assert "summary" in first
