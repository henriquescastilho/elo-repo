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


def test_telegram_webhook_basic_text(monkeypatch):
    calls: list[NormalizedMessage] = []

    async def fake_dispatch(message: NormalizedMessage):
        calls.append(message)
        return {"text": "oi!", "intent": "elo", "delivered": False}

    async def fake_responder_usuario(*args, **kwargs):
        return {"provider": "telegram", "audio_sent": False}

    monkeypatch.setattr(telegram_webhook, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(telegram_webhook, "dispatch_message", fake_dispatch)
    monkeypatch.setattr(telegram_webhook.response_service, "responder_usuario", fake_responder_usuario)

    client = TestClient(app)
    payload = {
        "update_id": 1,
        "message": {"message_id": 1, "chat": {"id": 123456}, "text": "teste telegram"},
    }

    resp = client.post("/webhook/telegram", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["intent"] == "elo"
    assert data["delivered"] is True

    assert len(calls) == 1
    normalized = calls[0]
    assert normalized.user_id == "tg:123456"
    assert normalized.type == "text"
    assert normalized.text == "teste telegram"
