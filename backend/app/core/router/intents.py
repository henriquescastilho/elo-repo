import logging
import re
from enum import Enum

from backend.app.core.config.bot_identity import BOT_NAME, DEFAULT_FLOW, PROJECTS
from backend.app.core.flows import elo_flow, oraculo_flow, votos_flow
from backend.app.models.schemas import NormalizedMessage

logger = logging.getLogger("elo.router")

VOTOS_KEYWORDS = (
    "votação",
    "votacoes",
    "plenário",
    "plenaria",
    "plenário",
    "plenario",
    "deputado",
    "deputada",
    "deputados",
    "deputadas",
    "camara",
    "câmara",
    "senado",
    "senador",
    "senadora",
    "pl",
    "projeto de lei",
    "proposicao",
    "proposição",
    "proposições",
    "como votou",
    "sessão",
    "sessao",
)


class Intent(str, Enum):
    ELO = "elo"
    VOTOS = "votos"
    ORACULO = "oraculo"


def normalize_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.lower()


def detect_intent(message: NormalizedMessage) -> Intent:
    # Se tiver mídia ou for tipo diferente de text, assume Oráculo
    if message.type in ("image", "audio", "file") or message.media_url:
        return Intent.ORACULO

    content = message.text or ""
    normalized = content.lower()
    if any(keyword in normalized for keyword in VOTOS_KEYWORDS):
        return Intent.VOTOS
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
