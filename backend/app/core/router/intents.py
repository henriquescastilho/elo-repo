import logging
import re
from enum import Enum

from backend.app.core.config.bot_identity import BOT_NAME, DEFAULT_FLOW, PROJECTS
from backend.app.core.flows import elo_flow, oraculo_flow, votos_flow
from backend.app.models.schemas import NormalizedMessage

logger = logging.getLogger("elo.router")

# Regex patterns for VOTOS intent
# Regex patterns for VOTOS intent
VOTOS_PATTERNS = [
    r"\b(pl|pec|plp|pln|pdl)\s*\d+",  # PL 1234, PEC 10
    r"\b(votação|votacao|voto|votou|votar)\b",
    r"\b(deputado|deputada|senador|senadora|parlamentar)\b",
    r"\b(camara|câmara|senado|congress|legislativo)\b",
    r"\b(projeto|projetos|proposição|proposicao)\b",
    r"\b(tramitação|tramitacao|relator|comissão|ccj)\b",
    r"\b(projeto de lei|proposta|ementa|inteiro teor)\b",
    r"\b(sessão|sessao|plenário|plenaria|pauta)\b",
    r"\b(partido|bancada|liderança)\b",
]

# Regex patterns for ELO intent (explicit citizen services)
ELO_PATTERNS = [
    r"\b(cpf|rg|cnh|passaporte|titulo de eleitor)\b",
    r"\b(sus|vacina|saude|saúde|medicamento|remédio)\b",
    r"\b(bolsa familia|auxilio|beneficio|inss|aposentadoria)\b",
    r"\b(seguro desemprego|fgts|pis|pasep)\b",
    r"\b(escola|matricula|enem|sisu|prouni)\b",
    r"\b(imposto|receita federal|leão|irpf)\b",
    r"\b(consumidor|procon|direito)\b",
]

# Regex patterns for ORACULO intent (links/media keywords)
ORACULO_PATTERNS = [
    r"(https?://[^\s]+)",  # Any URL
    r"\b(youtube\.com|youtu\.be)\b",
    r"\b(noticia|notícia|reportagem|materia|matéria)\b",
    r"\b(video|vídeo|foto|imagem|audio|áudio)\b",
    r"\b(analise|análise|resuma|resumo|explique este)\b",
]


class Intent(str, Enum):
    ELO = "elo"
    VOTOS = "votos"
    ORACULO = "oraculo"


def normalize_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.lower()


def detect_intent(message: NormalizedMessage) -> Intent:
    # 1. ORACULO: Media types (image, audio, file) or explicit media_url
    if message.type in ("image", "audio", "file") or message.media_url:
        return Intent.ORACULO
    
    content = message.text or ""
    normalized = normalize_text(content)

    # 2. ORACULO: Check for URLs or specific media keywords in text
    for pattern in ORACULO_PATTERNS:
        if re.search(pattern, normalized):
            return Intent.ORACULO

    # 3. VOTOS: Legislative context
    for pattern in VOTOS_PATTERNS:
        if re.search(pattern, normalized):
            return Intent.VOTOS

    # 4. ELO: Citizen services (Explicit)
    for pattern in ELO_PATTERNS:
        if re.search(pattern, normalized):
            return Intent.ELO

    # 5. Fallback: ELO (Default for general questions)
    return Intent.ELO


async def dispatch_message(message: NormalizedMessage) -> dict:
    """
    Route message to the correct flow and return a dict with the response.
    """
    intent = detect_intent(message)
    logger.info("Roteando mensagem user=%s intent=%s", message.user_id, intent.value)

    try:
        if intent == Intent.VOTOS:
            result = await votos_flow.handle_message(message)
        elif intent == Intent.ORACULO:
            result = await oraculo_flow.handle_message(message)
        else:
            result = await elo_flow.handle_message(message)

        if isinstance(result, dict):
            text = result.get("text") or ""
            delivered = bool(result.get("delivered"))
        else:
            text = result
            delivered = False

    except Exception as exc:
        logger.error("Erro no fluxo %s: %s", intent.value, exc)
        text = "Desculpe, tive um erro interno. Tente novamente mais tarde."
        delivered = False

    return {
        "text": text,
        "intent": intent.value,
        "bot_name": BOT_NAME,
        "project": PROJECTS[1] if intent == Intent.VOTOS else DEFAULT_FLOW,
        "delivered": delivered,
    }
