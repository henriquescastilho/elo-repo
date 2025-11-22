"""Simple semantic cache backed by Redis when available."""

import json
import logging
from typing import Optional

from backend.app.config import get_settings

logger = logging.getLogger(__name__)

try:
    from redis import asyncio as redis_asyncio  # type: ignore
except ImportError:  # pragma: no cover - redis optional during tests
    redis_asyncio = None

settings = get_settings()
redis_client = None
if redis_asyncio and settings.redis_url:
    redis_client = redis_asyncio.from_url(settings.redis_url, decode_responses=True)
_user_state_memory: dict[str, dict] = {}


async def get_cached_answer(hash_key: str) -> Optional[str]:
    if not redis_client:
        return None
    try:
        return await redis_client.get(hash_key)
    except Exception as exc:  # pragma: no cover - network failures
        logger.warning("Redis get failed: %s", exc)
        return None


async def set_cached_answer(hash_key: str, answer: str, ttl: int = 600) -> None:
    if not redis_client:
        return
    try:
        await redis_client.set(hash_key, answer, ex=ttl)
    except Exception as exc:  # pragma: no cover - network failures
        logger.warning("Redis set failed: %s", exc)


USER_STATE_PREFIX = "user_state:"


async def get_user_state(user_id: str) -> Optional[dict]:
    if redis_client:
        try:
            raw = await redis_client.get(f"{USER_STATE_PREFIX}{user_id}")
        except Exception as exc:  # pragma: no cover - network failures
            logger.warning("Redis get user state failed: %s", exc)
            return None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid user state json for user=%s", user_id)
            return None
    return _user_state_memory.get(user_id)


async def set_user_state(user_id: str, state: dict, ttl: int = 86400) -> None:
    if redis_client:
        try:
            await redis_client.set(
                f"{USER_STATE_PREFIX}{user_id}", json.dumps(state), ex=ttl
            )
        except Exception as exc:  # pragma: no cover - network failures
            logger.warning("Redis set user state failed: %s", exc)
        return
    _user_state_memory[user_id] = state.copy()
