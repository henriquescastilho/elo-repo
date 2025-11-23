"""
Feedback service for collecting and aggregating user sentiment on bills.
Adapted for ELO-REPO (FastAPI + Redis).
"""

import logging
from typing import Dict
from collections import Counter
from backend.app.services import cache_service

logger = logging.getLogger(__name__)

VALID_SENTIMENTS = {"concordo", "discordo", "neutro"}

async def save_feedback(user_id: str, bill_id: str, sentiment: str) -> bool:
    """Save user feedback on a bill using Redis if available."""
    try:
        sentiment_normalized = sentiment.lower().strip()
        if sentiment_normalized not in VALID_SENTIMENTS:
            logger.warning(f"Invalid sentiment: {sentiment_normalized}")
            return False

        # Redis implementation
        if cache_service.redis_client:
            # Use a Hash to store user feedback for a bill: key=bill:{id}:feedback, field=user_id, value=sentiment
            key = f"bill:{bill_id}:feedback"
            await cache_service.redis_client.hset(key, user_id, sentiment_normalized)
            logger.info(f"💬 User {user_id} feedback on {bill_id}: {sentiment_normalized} (Redis)")
            return True
        
        # Fallback: In-memory (ephemeral) - mostly for dev/testing without Redis
        # We use a global dict in this module for simplicity if Redis is missing
        if not hasattr(save_feedback, "_memory_store"):
            save_feedback._memory_store = {}
        
        key = f"{bill_id}:{user_id}"
        save_feedback._memory_store[key] = sentiment_normalized
        logger.info(f"💬 User {user_id} feedback on {bill_id}: {sentiment_normalized} (Memory)")
        return True

    except Exception as e:
        logger.error(f"Error saving feedback for user {user_id} on {bill_id}: {e}", exc_info=True)
        return False

async def get_sentiment_summary(bill_id: str) -> Dict[str, int]:
    """Get aggregated sentiment summary for a bill."""
    try:
        sentiments = []
        
        if cache_service.redis_client:
            key = f"bill:{bill_id}:feedback"
            # Get all fields (user_ids) and values (sentiments)
            feedback_dict = await cache_service.redis_client.hgetall(key)
            if feedback_dict:
                sentiments = list(feedback_dict.values())
        else:
            # Memory fallback
            store = getattr(save_feedback, "_memory_store", {})
            prefix = f"{bill_id}:"
            sentiments = [v for k, v in store.items() if k.startswith(prefix)]

        counts = Counter(sentiments)
        summary = {
            "concordo": counts.get("concordo", 0),
            "discordo": counts.get("discordo", 0),
            "neutro": counts.get("neutro", 0),
            "total": len(sentiments),
        }
        return summary
        
    except Exception as e:
        logger.error(f"Error getting sentiment summary for {bill_id}: {e}", exc_info=True)
        return {"concordo": 0, "discordo": 0, "neutro": 0, "total": 0}
