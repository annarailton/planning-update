"""Redis connection management.

Provides async Redis client singleton for the application.
"""

import logging
from typing import Optional

from redis.asyncio import Redis

from core.config import get_settings

logger = logging.getLogger(__name__)

# Singleton Redis client
_redis_client: Optional[Redis] = None


async def init_redis() -> Redis:
    """Initialize Redis connection.

    Returns:
        Redis client instance
    """
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    settings = get_settings()
    _redis_client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    # Test connection
    try:
        await _redis_client.ping()
        logger.info("Redis connection initialized")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise

    return _redis_client


async def get_redis() -> Redis:
    """Get Redis client singleton.

    Creates connection on first call.

    Returns:
        Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        return await init_redis()

    return _redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client

    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed")
