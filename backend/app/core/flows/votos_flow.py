from backend.app.config import get_settings
from backend.app.core.config.bot_identity import BOT_NAME
from backend.app.models.schemas import NormalizedMessage
from backend.app.services import llm_service, response_service


async def handle_message(message: NormalizedMessage) -> dict[str, object]:
    """
    Handle flow focused on votações e parlamento (VOTOS Interativo).
    """
    user_text = (message.text or "").strip()
    answer = await llm_service.answer_user_question(user_text, context=message, flow="votos", bot_name=BOT_NAME)

    settings = get_settings()
    mode = "texto+audio" if settings.send_audio_default else "texto"
    await response_service.responder_usuario(
        to=message.user_id,
        text=answer,
        mode=mode,
        context=message,
    )

    return {"text": answer, "delivered": True}
