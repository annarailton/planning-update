"""Redis client singleton management.

Provides async Redis client initialization and access.
Supports key prefixing for environment isolation (e.g., prod:, staging:, dev:).
"""

import asyncio
import logging
import os
from typing import Optional
from urllib.parse import urlparse

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# Singleton Redis client with lock for thread-safe initialization
_redis_client: Optional[Redis] = None
_redis_lock = asyncio.Lock()

# Key prefix for environment isolation (set via REDIS_KEY_PREFIX env var)
# Initialize from env var so prefix_key() works even without init_redis()
_key_prefix: str = os.getenv("REDIS_KEY_PREFIX", "")


def get_key_prefix() -> str:
    """Get the current Redis key prefix.

    Returns:
        Key prefix string (e.g., "prod:", "staging:", "feature-x:")
    """
    return _key_prefix


def prefix_key(key: str) -> str:
    """Apply key prefix to a Redis key.

    Args:
        key: The original key

    Returns:
        Prefixed key (e.g., "prod:jobs" for prefix "prod:" and key "jobs")
    """
    if _key_prefix:
        return f"{_key_prefix}{key}"
    return key


async def init_redis(redis_url: str, key_prefix: Optional[str] = None) -> Redis:
    """Initialize Redis connection.

    Uses double-check locking pattern for thread-safe singleton initialization.

    Args:
        redis_url: Redis connection URL (e.g., "redis://localhost:6379")
        key_prefix: Optional key prefix for environment isolation.
                   If not provided, uses REDIS_KEY_PREFIX env var.

    Returns:
        Redis client instance

    Raises:
        Exception: If connection fails
    """
    global _redis_client, _key_prefix

    # Fast path - already initialized
    if _redis_client is not None:
        return _redis_client

    # Slow path - need to initialize with lock
    async with _redis_lock:
        # Double-check after acquiring lock
        if _redis_client is not None:
            return _redis_client

        # Set key prefix from argument or environment
        _key_prefix = key_prefix if key_prefix is not None else os.getenv("REDIS_KEY_PREFIX", "")

        _redis_client = Redis.from_url(
            redis_url,
            decode_responses=True,
        )

        # Test connection
        try:
            await _redis_client.ping()
            # Log URL without credentials
            parsed = urlparse(redis_url)
            safe_url = f"{parsed.scheme}://{parsed.hostname}:{parsed.port or 6379}"
            prefix_info = f" (prefix: {_key_prefix})" if _key_prefix else ""
            logger.info(f"Redis connection initialized: {safe_url}{prefix_info}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            _redis_client = None
            raise

        return _redis_client


async def get_redis() -> Redis:
    """Get Redis client singleton.

    Returns:
        Redis client instance

    Raises:
        RuntimeError: If Redis not initialized
    """
    global _redis_client

    if _redis_client is None:
        raise RuntimeError(
            "Redis not initialized. Call init_redis() first."
        )

    return _redis_client


def get_redis_or_none() -> Optional[Redis]:
    """Get Redis client or None if not initialized.

    Safe to use when Redis may not be available.

    Returns:
        Redis client instance or None
    """
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client, _key_prefix

    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        _key_prefix = ""
        logger.info("Redis connection closed")
