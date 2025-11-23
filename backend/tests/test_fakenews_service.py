import pytest
from unittest.mock import AsyncMock, patch

from backend.app.models.schemas import NormalizedMessage
from backend.app.services import fakenews_service


@pytest.mark.anyio
async def test_fakenews_analyze_basic_structure():
    msg = NormalizedMessage(user_id="u1", type="text", text="O deputado X acabou com o SUS ontem.")

    # Mock DataHub to avoid real HTTP
    with patch(
        "backend.app.services.datahub.aggregator.search_all_sources",
        new_callable=AsyncMock,
    ) as mock_search_all, patch(
        "backend.app.services.llm_service._call_llm_openai",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_search_all.return_value = [
            {
                "id": "1",
                "title": "Lei do SUS",
                "summary": "Regula o Sistema Único de Saúde",
                "year": 1990,
                "source": "camara",
                "url": "http://example.com",
            }
        ]
        mock_llm.return_value = (
            '{"risk": "alto", "explanation": "Informação falsa sobre o fim do SUS.", '
            '"safe_answer": "O SUS continua em funcionamento.", "should_warn": true}',
            True,
        )

        result = await fakenews_service.analyze_text(msg.text or "", context=msg)

    assert result["risk"] == "alto"
    assert "SUS" in result["safe_answer"]
    assert result["should_warn"] is True


@pytest.mark.anyio
async def test_fakenews_handles_bad_json_gracefully():
    msg = NormalizedMessage(user_id="u2", type="text", text="Texto qualquer.")

    with patch(
        "backend.app.services.datahub.aggregator.search_all_sources",
        new_callable=AsyncMock,
    ) as mock_search_all, patch(
        "backend.app.services.llm_service._call_llm_openai",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_search_all.return_value = []
        # LLM responde com texto inválido
        mock_llm.return_value = ("isso não é JSON", True)

        result = await fakenews_service.analyze_text(msg.text or "", context=msg)

    assert result["risk"] == "baixo"
    assert result["should_warn"] is False

