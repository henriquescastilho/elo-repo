import pytest
from backend.app.core.router.intents import detect_intent, Intent
from backend.app.models.schemas import NormalizedMessage

def test_detect_intent_votos():
    # Test Legislative keywords
    msg = NormalizedMessage(user_id="test", text="Como votou o deputado X na PL 1234?")
    assert detect_intent(msg) == Intent.VOTOS

    msg = NormalizedMessage(user_id="test", text="Qual a tramitação da PEC 10?")
    assert detect_intent(msg) == Intent.VOTOS

    msg = NormalizedMessage(user_id="test", text="Agenda da comissão de constituição e justiça")
    assert detect_intent(msg) == Intent.VOTOS

def test_detect_intent_elo_explicit():
    # Test Citizen Services keywords
    msg = NormalizedMessage(user_id="test", text="Como tirar o CPF?")
    assert detect_intent(msg) == Intent.ELO

    msg = NormalizedMessage(user_id="test", text="Calendário do Bolsa Família")
    assert detect_intent(msg) == Intent.ELO

    msg = NormalizedMessage(user_id="test", text="Onde tomar vacina da gripe?")
    assert detect_intent(msg) == Intent.ELO

def test_detect_intent_oraculo_media():
    # Test Media types
    msg = NormalizedMessage(user_id="test", text="", type="image", media_url="http://example.com/img.jpg")
    assert detect_intent(msg) == Intent.ORACULO

    msg = NormalizedMessage(user_id="test", text="", type="audio", media_url="http://example.com/audio.ogg")
    assert detect_intent(msg) == Intent.ORACULO

def test_detect_intent_oraculo_text():
    # Test Media keywords/URLs in text
    msg = NormalizedMessage(user_id="test", text="Analise esta imagem: https://site.com/foto.jpg")
    assert detect_intent(msg) == Intent.ORACULO

    msg = NormalizedMessage(user_id="test", text="Resuma este vídeo do youtube.com/watch?v=123")
    assert detect_intent(msg) == Intent.ORACULO

    msg = NormalizedMessage(user_id="test", text="O que diz essa notícia?")
    assert detect_intent(msg) == Intent.ORACULO

def test_detect_intent_fallback():
    # Test Fallback (Ambiguous or General)
    msg = NormalizedMessage(user_id="test", text="Bom dia, tudo bem?")
    assert detect_intent(msg) == Intent.ELO

    msg = NormalizedMessage(user_id="test", text="Qual o sentido da vida?")
    assert detect_intent(msg) == Intent.ELO
