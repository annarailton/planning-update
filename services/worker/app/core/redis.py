"""Redis connection management for worker service.

Delegates to the shared packages/redis module for connection management.
"""

from redis.asyncio import Redis

from core.config import get_settings
from packages.redis import close_redis, get_redis
from packages.redis import init_redis as _init_redis


async def init_redis() -> Redis:
    """Initialize Redis connection via shared package.

    Returns:
        Redis client instance
    """
    settings = get_settings()
    return await _init_redis(settings.redis_url)


# Re-export from packages/redis
__all__ = ["init_redis", "get_redis", "close_redis"]
