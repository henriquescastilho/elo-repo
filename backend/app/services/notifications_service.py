"""Integração com n8n desativada; notificações hoje são apenas logs internos."""

import logging

logger = logging.getLogger(__name__)


async def send_proactive_update(user_id: str, message: str) -> None:
    logger.info("[notifications] Atualização interna (n8n desativado) user=%s msg=%s", user_id, message)


async def send_welcome(user_id: str, name: str) -> None:
    logger.info("[notifications] Boas-vindas interna (n8n desativado) user=%s name=%s", user_id, name)


async def send_pl_update(user_id: str, message: str) -> None:
    logger.info("[notifications] Atualização PL interna (n8n desativado) user=%s msg=%s", user_id, message)


# Mantendo assinatura para futuras integrações externas se necessário.
