import pytest

from backend.app.core.flows import oraculo_flow
from backend.app.models.schemas import NormalizedMessage
from backend.app.services import llm_service, stt_service


@pytest.mark.anyio
async def test_oraculo_audio_transcreve_se_preciso(monkeypatch):
    msg = NormalizedMessage(
        user_id="u_audio",
        type="audio",
        media_bytes=b"fake-audio-bytes",
        mime_type="audio/ogg",
        text=None,
    )

    async def fake_transcribe_audio(path: str) -> str:
        # Apenas garante que um caminho temporário foi criado
        assert path.endswith(".ogg")
        return "TRANSCRICAO DO AUDIO"

    async def fake_answer_user_question(user_text, context=None, flow=None, bot_name=None):
        assert flow == "oraculo"
        assert isinstance(context, oraculo_flow.OracleContext)

        ctx = context.contexto_oraculo
        assert ctx["tipo_arquivo"] == "audio"
        assert "TRANSCRICAO DO AUDIO" in ctx["texto_extraido"]
        return "ok-audio"

    monkeypatch.setattr(stt_service, "transcribe_audio", fake_transcribe_audio)
    monkeypatch.setattr(llm_service, "answer_user_question", fake_answer_user_question)

    result = await oraculo_flow.handle_message(msg)
    assert result == "ok-audio"

