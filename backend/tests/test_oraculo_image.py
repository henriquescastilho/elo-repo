import pytest

from backend.app.core.flows import oraculo_flow
from backend.app.models.schemas import NormalizedMessage
from backend.app.services import llm_service, vision_service


@pytest.mark.anyio
async def test_oraculo_image_usa_vision_service(monkeypatch):
    msg = NormalizedMessage(
        user_id="u_img",
        type="image",
        media_bytes=b"fake-image-bytes",
        mime_type="image/jpeg",
        media_url="http://fake/img.jpg",
    )

    async def fake_analyze_image(image_bytes=None, image_url=None, prompt=None):
        assert image_bytes == b"fake-image-bytes"
        assert image_url == "http://fake/img.jpg"
        return "DESCRICAO TECNICA DA IMAGEM"

    async def fake_answer_user_question(user_text, context=None, flow=None, bot_name=None):
        assert flow == "oraculo"
        assert isinstance(context, oraculo_flow.OracleContext)

        ctx = context.contexto_oraculo
        assert ctx["tipo_arquivo"] == "image"
        assert "DESCRICAO TECNICA" in ctx["texto_extraido"]
        return "ok-image"

    monkeypatch.setattr(vision_service, "analyze_image", fake_analyze_image)
    monkeypatch.setattr(llm_service, "answer_user_question", fake_answer_user_question)

    result = await oraculo_flow.handle_message(msg)
    assert result == "ok-image"

