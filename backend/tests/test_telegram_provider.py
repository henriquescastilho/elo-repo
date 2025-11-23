import pytest

from backend.app.services import telegram_provider


class DummySettings:
    telegram_enabled: bool = True
    telegram_sandbox_mode: bool = False
    telegram_bot_token: str | None = "TOKEN"
    telegram_base_url: str = "https://api.telegram.org"


class DummySandboxSettings(DummySettings):
    telegram_sandbox_mode = True


class DummyResponse:
    def __init__(self, status_code=200, json_data=None, text="ok"):
        self.status_code = status_code
        self._json = json_data or {"ok": True}
        self.text = text

    def json(self):
        return self._json


class DummyClient:
    def __init__(self, calls):
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, data=None, files=None):
        self.calls.append({"url": url, "data": data, "files": files})
        return DummyResponse()


@pytest.mark.anyio
async def test_send_text_and_media(monkeypatch):
    calls = []

    monkeypatch.setattr(telegram_provider, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(telegram_provider.httpx, "AsyncClient", lambda **_: DummyClient(calls))

    ok_text = await telegram_provider.send_text("123", "olá")
    ok_audio = await telegram_provider.send_audio("123", b"bytes", filename="audio.ogg")
    ok_image = await telegram_provider.send_image("123", b"img", filename="img.jpg")

    assert ok_text is True
    assert ok_audio is True
    assert ok_image is True
    assert len(calls) == 3
    assert calls[0]["url"].endswith("/botTOKEN/sendMessage")
    assert calls[0]["data"]["text"] == "olá"
    assert calls[1]["files"]["audio"][0] == "audio.ogg"
    assert calls[2]["files"]["photo"][0] == "img.jpg"


@pytest.mark.anyio
async def test_sandbox_mode_skips(monkeypatch):
    calls = []
    monkeypatch.setattr(telegram_provider, "get_settings", lambda: DummySandboxSettings())
    monkeypatch.setattr(telegram_provider.httpx, "AsyncClient", lambda **_: DummyClient(calls))

    ok = await telegram_provider.send_text("123", "sandbox")
    assert ok is True
    assert calls == []
