from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.schemas import NormalizedMessage
from backend.app.routes import telegram_webhook


class DummySettings:
    telegram_webhook_secret = None
    telegram_sandbox_mode = True
    telegram_bot_token = None
    telegram_base_url = "https://api.telegram.org"
    send_audio_default = False


def test_telegram_webhook_document_triggers_oraculo(monkeypatch):
    calls: list[NormalizedMessage] = []

    async def fake_dispatch(message: NormalizedMessage):
        calls.append(message)
        return {"text": "analisando documento", "intent": "oraculo", "delivered": False}

    async def fake_responder_usuario(*args, **kwargs):
        return {"provider": "telegram", "audio_sent": False}

    monkeypatch.setattr(telegram_webhook, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(telegram_webhook, "dispatch_message", fake_dispatch)
    monkeypatch.setattr(telegram_webhook.response_service, "responder_usuario", fake_responder_usuario)

    client = TestClient(app)
    payload = {
        "update_id": 2,
        "message": {
            "message_id": 2,
            "chat": {"id": 999},
            "document": {"file_id": "FILE123", "mime_type": "application/pdf", "file_name": "teste.pdf"},
        },
    }

    resp = client.post("/webhook/telegram", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["intent"] == "oraculo"
    assert data["delivered"] is True

    assert len(calls) == 1
    normalized = calls[0]
    assert normalized.user_id == "tg:999"
    assert normalized.type == "file"
    assert normalized.media_bytes is None  # sandbox não baixa arquivo
