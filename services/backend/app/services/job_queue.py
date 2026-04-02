"""Job queue for Redis Stream operations.

Handles all Redis Stream and Pub/Sub operations for jobs.
Pure queue layer - no database logic.
"""

import json
import logging
from typing import Any, Optional

from redis.asyncio import Redis

from packages.redis.client import prefix_key
from packages.redis.pubsub import get_job_channel

logger = logging.getLogger(__name__)

# Redis Stream and consumer group names (prefixed for namespace isolation)
STREAM_NAME = prefix_key("jobs")
GROUP_NAME = "workers"


class JobQueue:
    """Queue for job Redis operations."""

    def __init__(self, redis: Redis):
        """Initialize with Redis client.

        Args:
            redis: Redis client instance
        """
        self.redis = redis

    async def ensure_consumer_group(self) -> None:
        """Ensure the consumer group exists."""
        try:
            await self.redis.xgroup_create(
                name=STREAM_NAME,
                groupname=GROUP_NAME,
                id="0",
                mkstream=True,
            )
            logger.info(f"Created consumer group '{GROUP_NAME}'")
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.debug(f"Consumer group '{GROUP_NAME}' already exists")
            else:
                raise

    async def enqueue(
        self,
        job_id: str,
        job_type: str,
        payload: dict[str, Any],
    ) -> str:
        """Add a job to the queue.

        Args:
            job_id: Job ID
            job_type: Type of job
            payload: Job payload

        Returns:
            Stream entry ID
        """
        entry_id = await self.redis.xadd(
            STREAM_NAME,
            {
                "job_id": job_id,
                "job_type": job_type,
                "payload": json.dumps(payload),
            },
        )
        logger.info(f"Enqueued job {job_id} to Redis Stream (entry={entry_id})")
        return entry_id

    async def consume(
        self,
        consumer_id: str,
        block_ms: int = 5000,
        count: int = 1,
    ) -> list[tuple[str, dict[str, str]]]:
        """Consume jobs from the queue.

        Blocking read from Redis Stream using consumer group.

        Args:
            consumer_id: Unique consumer identifier
            block_ms: Milliseconds to block waiting for messages
            count: Max messages to read

        Returns:
            List of (entry_id, data) tuples
        """
        messages = await self.redis.xreadgroup(
            groupname=GROUP_NAME,
            consumername=consumer_id,
            streams={STREAM_NAME: ">"},
            block=block_ms,
            count=count,
        )

        if not messages:
            return []

        # Flatten the nested structure
        result = []
        for stream_name, entries in messages:
            for entry_id, data in entries:
                result.append((entry_id, data))

        return result

    async def acknowledge(self, entry_id: str) -> None:
        """Acknowledge a processed job.

        Args:
            entry_id: Stream entry ID to acknowledge
        """
        await self.redis.xack(STREAM_NAME, GROUP_NAME, entry_id)
        logger.debug(f"Acknowledged entry {entry_id}")

    async def claim_stale(
        self,
        consumer_id: str,
        min_idle_ms: int,
        count: int = 5,
    ) -> list[tuple[str, dict[str, str]]]:
        """Claim stale jobs that other consumers abandoned.

        Args:
            consumer_id: Consumer claiming the jobs
            min_idle_ms: Minimum idle time in milliseconds
            count: Max jobs to claim

        Returns:
            List of (entry_id, data) tuples
        """
        try:
            result = await self.redis.xautoclaim(
                name=STREAM_NAME,
                groupname=GROUP_NAME,
                consumername=consumer_id,
                min_idle_time=min_idle_ms,
                start_id="0-0",
                count=count,
            )

            if result and len(result) > 1 and result[1]:
                claimed = result[1]
                for entry_id, _ in claimed:
                    logger.warning(f"Reclaimed stale job: {entry_id}")
                return claimed

        except Exception as e:
            logger.error(f"Error claiming stale jobs: {e}")

        return []

    async def publish_progress(
        self,
        job_id: str,
        progress: int | float,
        message: Optional[str] = None,
    ) -> None:
        """Publish progress update via Pub/Sub.

        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
            message: Optional progress message
        """
        await self.redis.publish(
            get_job_channel(job_id),
            json.dumps(
                {
                    "event": "progress",
                    "job_id": job_id,
                    "progress": progress,
                    "message": message,
                }
            ),
        )

    async def publish_complete(
        self,
        job_id: str,
        result: Any,
    ) -> None:
        """Publish completion via Pub/Sub.

        Args:
            job_id: Job ID
            result: Job result data
        """
        await self.redis.publish(
            get_job_channel(job_id),
            json.dumps(
                {
                    "event": "complete",
                    "job_id": job_id,
                    "result": result,
                }
            ),
        )

    async def publish_error(
        self,
        job_id: str,
        error: str,
    ) -> None:
        """Publish error via Pub/Sub.

        Args:
            job_id: Job ID
            error: Error message
        """
        await self.redis.publish(
            get_job_channel(job_id),
            json.dumps(
                {
                    "event": "error",
                    "job_id": job_id,
                    "error": error,
                }
            ),
        )


def create_job_queue(redis: Redis) -> JobQueue:
    """Create a JobQueue instance.

    Args:
        redis: Redis client

    Returns:
        JobQueue instance
    """
    return JobQueue(redis)
