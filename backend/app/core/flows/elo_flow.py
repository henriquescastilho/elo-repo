from backend.app.core.config.bot_identity import BOT_NAME
from backend.app.models.schemas import NormalizedMessage
from backend.app.services import llm_service
from backend.app.services import fakenews_service


async def handle_message(message: NormalizedMessage) -> str:
    """
    Handle general civic assistance (ELO) flow.
    """
    user_text = message.text or ""
    # Primeiro, verificar risco de desinformação / fake news
    analysis = await fakenews_service.analyze_text(user_text, context=message)

    # Risco ALTO: prioriza aviso e resposta segura do verificador
    if analysis["risk"] == "alto":
        warning_prefix = (
            "⚠️ Aviso importante: encontrei indícios fortes de possível desinformação "
            "ou informação imprecisa nesse conteúdo.\n\n"
        )
        explanation = analysis["explanation"]
        safe_answer = analysis["safe_answer"] or ""
        return f"{warning_prefix}{explanation}\n\nResposta segura do ELO:\n{safe_answer}".strip()

    # Risco MÉDIO: avisa que está verificando, mas segue com a resposta normal do ELO
    if analysis["risk"] == "medio":
        base_answer = await llm_service.answer_user_question(
            user_text, context=message, flow="elo", bot_name=BOT_NAME
        )
        explanation = analysis["explanation"]
        prefix = (
            "Estou verificando essa informação com fontes oficiais e confiáveis. "
            "Veja o que encontrei até agora:\n\n"
        )
        return f"{prefix}{explanation}\n\nResposta do ELO:\n{base_answer}".strip()

    # Risco BAIXO: fluxo normal
    return await llm_service.answer_user_question(
        user_text, context=message, flow="elo", bot_name=BOT_NAME
    )
