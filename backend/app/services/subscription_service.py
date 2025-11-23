"""
Subscription service for managing user topic subscriptions.
Adapted for ELO-REPO (FastAPI + Redis).
"""

import logging
from typing import List
from backend.app.services import cache_service

logger = logging.getLogger(__name__)

async def subscribe_topic(user_id: str, topic: str) -> bool:
    """Subscribe a user to a legislative topic."""
    try:
        topic_normalized = topic.lower().strip()
        
        if cache_service.redis_client:
            # Use a Set to store subscriptions: key=user:{id}:subscriptions
            key = f"user:{user_id}:subscriptions"
            await cache_service.redis_client.sadd(key, topic_normalized)
            logger.info(f"✅ User {user_id} subscribed to topic: {topic_normalized} (Redis)")
            return True
            
        # Fallback: In-memory
        if not hasattr(subscribe_topic, "_memory_store"):
            subscribe_topic._memory_store = {}
        
        existing = subscribe_topic._memory_store.get(user_id, set())
        existing.add(topic_normalized)
        subscribe_topic._memory_store[user_id] = existing
        logger.info(f"✅ User {user_id} subscribed to topic: {topic_normalized} (Memory)")
        return True
        
    except Exception as e:
        logger.error(f"Error subscribing user {user_id} to {topic}: {e}", exc_info=True)
        return False

async def unsubscribe_topic(user_id: str, topic: str) -> bool:
    """Unsubscribe a user from a legislative topic."""
    try:
        topic_normalized = topic.lower().strip()
        
        if cache_service.redis_client:
            key = f"user:{user_id}:subscriptions"
            result = await cache_service.redis_client.srem(key, topic_normalized)
            if result > 0:
                logger.info(f"❌ User {user_id} unsubscribed from topic: {topic_normalized} (Redis)")
                return True
            return False
            
        # Fallback
        store = getattr(subscribe_topic, "_memory_store", {})
        existing = store.get(user_id, set())
        if topic_normalized in existing:
            existing.remove(topic_normalized)
            logger.info(f"❌ User {user_id} unsubscribed from topic: {topic_normalized} (Memory)")
            return True
        return False
        
    except Exception as e:
        logger.error(f"Error unsubscribing user {user_id} from {topic}: {e}", exc_info=True)
        return False

async def get_subscriptions(user_id: str) -> List[str]:
    """Get all topics a user is subscribed to."""
    try:
        if cache_service.redis_client:
            key = f"user:{user_id}:subscriptions"
            # SMEMBERS returns a set of strings
            subs = await cache_service.redis_client.smembers(key)
            return list(subs)
            
        # Fallback
        store = getattr(subscribe_topic, "_memory_store", {})
        return list(store.get(user_id, set()))
        
    except Exception as e:
        logger.error(f"Error getting subscriptions for user {user_id}: {e}", exc_info=True)
        return []
