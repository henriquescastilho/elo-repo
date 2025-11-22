from backend.app.core.config.bot_identity import BOT_NAME
from backend.app.models.schemas import NormalizedMessage
from backend.app.services import llm_service


async def handle_message(message: NormalizedMessage) -> str:
    """
    Handle Oracle Mode flow (documents, media, etc).
    """
    user_text = message.text or ""
    # Se houver media_url, poderíamos adicionar ao texto ou processar separadamente.
    # Por enquanto, passamos o contexto completo para o llm_service.
    
    return await llm_service.answer_user_question(
        user_text, 
        context=message, 
        flow="oraculo", 
        bot_name=BOT_NAME
    )
