"""Optional Redis package for caching, pub/sub, and job queue.

This package provides:
- Async Redis client singleton
- Pub/Sub helpers for real-time events
- Job queue using Redis Streams

It is OPTIONAL - the application works without it if redis is not installed
or not configured (FEATURE_REDIS=false).

The package gracefully handles the case where redis is not installed.

Usage:
    from packages.redis import (
        is_redis_available,
        init_redis,
        get_redis,
        close_redis,
        JobQueue,
        publish_job_progress,
    )

    # Check if Redis is available
    if is_redis_available():
        await init_redis("redis://localhost:6379")
        redis = await get_redis()

Configuration:
    Set FEATURE_REDIS=true and REDIS_URL to enable.
"""

import os
import logging

logger = logging.getLogger(__name__)

# Check if redis is installed
try:
    from redis.asyncio import Redis  # noqa: F401

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.debug("redis not installed - Redis features disabled")


def is_redis_available() -> bool:
    """Check if Redis package is installed.

    Returns:
        True if redis package is available
    """
    return REDIS_AVAILABLE


def is_redis_enabled() -> bool:
    """Check if Redis is enabled via feature flag.

    Redis is enabled when:
    1. redis package is installed
    2. FEATURE_REDIS env var is true

    Returns:
        True if Redis is enabled and available
    """
    if not REDIS_AVAILABLE:
        return False

    feature_redis = os.getenv("FEATURE_REDIS", "false").lower() in ("true", "1", "yes")
    return feature_redis


# Conditional imports - only available if redis is installed
if REDIS_AVAILABLE:
    from .client import (
        init_redis,
        get_redis,
        get_redis_or_none,
        close_redis,
        get_key_prefix,
        prefix_key,
    )
    from .pubsub import (
        # Channel generators
        get_job_channel,
        get_user_files_channel,
        get_project_channel,
        get_workflow_channel,
        # Job events
        publish_job_progress,
        publish_job_complete,
        publish_job_error,
        # File events
        publish_file_status,
        publish_file_complete,
        publish_file_error,
        # Project events
        publish_project_status,
        publish_project_progress,
        publish_project_complete,
        publish_project_error,
    )
    from .queue import JobQueue, create_job_queue

    __all__ = [
        # Feature checks
        "is_redis_available",
        "is_redis_enabled",
        "REDIS_AVAILABLE",
        # Client
        "init_redis",
        "get_redis",
        "get_redis_or_none",
        "close_redis",
        "get_key_prefix",
        "prefix_key",
        # Channels
        "get_job_channel",
        "get_user_files_channel",
        "get_project_channel",
        "get_workflow_channel",
        # Job events
        "publish_job_progress",
        "publish_job_complete",
        "publish_job_error",
        # File events
        "publish_file_status",
        "publish_file_complete",
        "publish_file_error",
        # Project events
        "publish_project_status",
        "publish_project_progress",
        "publish_project_complete",
        "publish_project_error",
        # Queue
        "JobQueue",
        "create_job_queue",
    ]
else:
    __all__ = [
        "is_redis_available",
        "is_redis_enabled",
        "REDIS_AVAILABLE",
    ]
