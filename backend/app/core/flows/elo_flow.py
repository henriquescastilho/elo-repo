from backend.app.core.config.bot_identity import BOT_NAME
from backend.app.models.schemas import NormalizedMessage
from backend.app.services import llm_service


async def handle_message(message: NormalizedMessage) -> str:
    """
    Handle general civic assistance (ELO) flow.
    """
    user_text = message.text or ""
    return await llm_service.answer_user_question(user_text, context=message, flow="elo", bot_name=BOT_NAME)
