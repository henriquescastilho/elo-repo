import pytest
from unittest.mock import patch, AsyncMock
from backend.app.services import rag_service

@pytest.mark.anyio
async def test_rag_search_legal_only():
    # Mock settings to use legal_only mode
    with patch("backend.app.services.rag_service.get_settings") as mock_settings:
        mock_settings.return_value.legal_data_source_mode = "legal_only"
        mock_settings.return_value.openai_api_key = "sk-test" # Fake key
        
        # Mock aggregator
        with patch("backend.app.services.datahub.aggregator.search_legal_sources", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = [{"id": "1", "title": "Test", "source": "camara"}]
            
            results = await rag_service.search_relevant_documents("test")
            
            mock_search.assert_called_once_with("test")
            assert len(results) == 1
            assert results[0]["id"] == "1"

@pytest.mark.anyio
async def test_rag_search_all():
    # Mock settings to use all mode
    with patch("backend.app.services.rag_service.get_settings") as mock_settings:
        mock_settings.return_value.legal_data_source_mode = "all"
        mock_settings.return_value.openai_api_key = "sk-test"
        
        # Mock aggregator
        with patch("backend.app.services.datahub.aggregator.search_all_sources", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = [{"id": "2", "title": "Test All", "source": "tse"}]
            
            results = await rag_service.search_relevant_documents("test")
            
            mock_search.assert_called_once_with("test")
            assert len(results) == 1
            assert results[0]["source"] == "tse"
