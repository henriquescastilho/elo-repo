import pytest

from backend.app.core.flows import oraculo_flow
from backend.app.models.schemas import NormalizedMessage
from backend.app.services import llm_service, pdf_service


@pytest.mark.anyio
async def test_oraculo_pdf_usa_pdf_service_e_modo_oraculo(monkeypatch):
    msg = NormalizedMessage(
        user_id="u_pdf",
        type="file",
        media_bytes=b"fake-pdf-bytes",
        mime_type="application/pdf",
        media_url="http://fake/doc.pdf",
    )

    def fake_extract_text(pdf_bytes, mime_type=None, filename=None):
        assert pdf_bytes == b"fake-pdf-bytes"
        return "CONTEUDO DO PDF", {"filename": filename or "doc.pdf", "num_pages": 1}

    async def fake_answer_user_question(user_text, context=None, flow=None, bot_name=None):
        # Deve estar no modo_oraculo
        assert flow == "oraculo"
        assert isinstance(context, oraculo_flow.OracleContext)

        ctx = context.contexto_oraculo
        assert ctx["tipo_arquivo"] == "file" or ctx["tipo_arquivo"] == "pdf"
        assert "CONTEUDO DO PDF" in ctx["texto_extraido"]
        assert ctx["metadados"]["num_pages"] == 1
        return "ok-pdf"

    monkeypatch.setattr(pdf_service, "extract_text", fake_extract_text)
    monkeypatch.setattr(llm_service, "answer_user_question", fake_answer_user_question)

    result = await oraculo_flow.handle_message(msg)
    assert result == "ok-pdf"

