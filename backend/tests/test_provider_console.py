import pytest
from backend.app.services import whatsapp_provider_console

@pytest.mark.anyio
async def test_console_send_text(capsys):
    await whatsapp_provider_console.send_text_message("5511999999999", "Hello Console")
    captured = capsys.readouterr()
    assert "[CONSOLE-OUT] to=5511999999999 msg=Hello Console" in captured.out

@pytest.mark.anyio
async def test_console_send_voice(capsys):
    await whatsapp_provider_console.send_message("", "http://audio.url", "5511999999999")
    captured = capsys.readouterr()
    assert "[CONSOLE-OUT-AUDIO] to=5511999999999 file=http://audio.url" in captured.out
