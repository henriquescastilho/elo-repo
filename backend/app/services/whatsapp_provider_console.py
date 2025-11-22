import logging
import os

logger = logging.getLogger(__name__)

async def send_text_message(user_id: str, text: str) -> None:
    """
    Simula envio de texto logando no console.
    """
    print(f"[CONSOLE-OUT] to={user_id} msg={text}")
    logger.info("[CONSOLE-OUT] to=%s msg=%s", user_id, text)

async def send_message(text: str, audio_url: str | None, user_id: str) -> None:
    """
    Simula envio de mensagem (texto ou áudio).
    """
    if text:
        await send_text_message(user_id, text)
    
    if audio_url:
        print(f"[CONSOLE-OUT-AUDIO] to={user_id} file={audio_url}")
        logger.info("[CONSOLE-OUT-AUDIO] to=%s file=%s", user_id, audio_url)
