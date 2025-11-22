import pytest

from backend.app.models.schemas import NormalizedMessage
from backend.app.services import cache_service, llm_service, rag_service


@pytest.mark.anyio
async def test_answer_user_question_with_mocked_dependencies(monkeypatch):
    async def mock_get_cached_answer(key: str):
        return None

    async def mock_set_cached_answer(key: str, answer: str, ttl: int = 600):
        return None

    async def mock_search_relevant_documents(query: str):
        return [{"title": "Mock", "content": "Conteúdo relevante"}]

    monkeypatch.setattr(cache_service, "get_cached_answer", mock_get_cached_answer)
    monkeypatch.setattr(cache_service, "set_cached_answer", mock_set_cached_answer)
    monkeypatch.setattr(rag_service, "search_relevant_documents", mock_search_relevant_documents)

    message = NormalizedMessage(user_id="123", type="text", text="Quais são meus direitos?")
    answer = await llm_service.answer_user_question(message.text or "", message)

    assert isinstance(answer, str)
    assert answer
