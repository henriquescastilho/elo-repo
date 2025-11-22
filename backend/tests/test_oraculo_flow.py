import pytest
from backend.app.core.router.intents import Intent, detect_intent
from backend.app.models.schemas import NormalizedMessage

def test_detect_intent_oraculo_media():
    # Test image detection
    msg_image = NormalizedMessage(user_id="123", type="image", media_url="http://fake/img.jpg")
    assert detect_intent(msg_image) == Intent.ORACULO

    # Test audio detection
    msg_audio = NormalizedMessage(user_id="123", type="audio", media_url="http://fake/audio.ogg")
    assert detect_intent(msg_audio) == Intent.ORACULO

def test_detect_intent_oraculo_file_url():
    # Test text message with media_url (e.g. PDF link)
    msg_file = NormalizedMessage(user_id="123", type="text", media_url="http://fake/doc.pdf")
    assert detect_intent(msg_file) == Intent.ORACULO

def test_detect_intent_elo_votos():
    # Ensure regressions didn't happen
    msg_elo = NormalizedMessage(user_id="123", text="como tirar cpf")
    assert detect_intent(msg_elo) == Intent.ELO

    msg_votos = NormalizedMessage(user_id="123", text="como votou o deputado X")
    assert detect_intent(msg_votos) == Intent.VOTOS
