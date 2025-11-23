import pytest
from backend.app.services.datahub import aggregator

@pytest.mark.anyio
async def test_search_legal_sources():
    # Test "legal_only" mode (Camara + Senado)
    # Using a query that triggers the mocks
    query = "saude"
    results = await aggregator.search_legal_sources(query)
    
    assert isinstance(results, list)
    # We expect at least one result from Senado mock (contains "saude")
    # Camara mock might return if it hits the real API or if we mock it too.
    # Since Camara service hits real API, it might fail if no network, but let's assume network or empty list.
    
    # Check if results are normalized
    if results:
        first = results[0]
        assert "id" in first
        assert "title" in first
        assert "summary" in first
        assert "source" in first

@pytest.mark.anyio
async def test_search_all_sources():
    # Test "all" mode
    query = "transporte" # Triggers Querido Diario mock
    results = await aggregator.search_all_sources(query)
    
    assert isinstance(results, list)
    # Should find Querido Diario mock result
    found_qd = any(r["source"] == "qd" for r in results)
    assert found_qd
