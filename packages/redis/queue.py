"""Redis Streams-based job queue.

Provides a reliable job queue using Redis Streams with consumer groups
for distributed processing.

Features:
- Durable job storage in Redis Streams
- Consumer groups for distributed workers
- Automatic retry of stale jobs
- Progress and completion events via pub/sub
"""

import json
import logging
from datetime import timedelta
from typing import Any, AsyncIterator, Optional
from uuid import UUID, uuid4

from redis.asyncio import Redis

from .client import get_redis, prefix_key
from .pubsub import publish_job_complete, publish_job_error, publish_job_progress

logger = logging.getLogger(__name__)

# Base stream and consumer group names (will be prefixed)
STREAM_NAME = "jobs"
GROUP_NAME = "workers"


class JobQueue:
    """Redis Streams-based job queue.

    Usage:
        queue = JobQueue(redis)

        # Enqueue a job
        job_id = await queue.enqueue("process_file", {"file_id": "..."})

        # Consume jobs (in worker)
        async for job in queue.consume("worker-1"):
            result = await process(job)
            await queue.acknowledge(job["id"])
    """

    def __init__(
        self,
        redis: Redis,
        stream_name: str = STREAM_NAME,
        group_name: str = GROUP_NAME,
    ):
        """Initialize job queue.

        Args:
            redis: Redis client instance
            stream_name: Name of the Redis stream (will be prefixed)
            group_name: Name of the consumer group (will be prefixed)
        """
        self.redis = redis
        # Apply key prefix for environment isolation
        self.stream_name = prefix_key(stream_name)
        self.group_name = prefix_key(group_name)

    async def ensure_group(self) -> None:
        """Ensure consumer group exists."""
        try:
            await self.redis.xgroup_create(
                self.stream_name,
                self.group_name,
                id="0",
                mkstream=True,
            )
            logger.info(f"Created consumer group: {self.group_name}")
        except Exception as e:
            # Group already exists is OK
            if "BUSYGROUP" not in str(e):
                raise

    async def enqueue(
        self,
        job_type: str,
        payload: dict[str, Any],
        job_id: Optional[UUID | str] = None,
        priority: int = 100,
    ) -> str:
        """Add a job to the queue.

        Args:
            job_type: Type of job (e.g., "process_file")
            payload: Job payload data
            job_id: Optional job ID (generated if not provided)
            priority: Job priority (lower = higher priority)

        Returns:
            Job ID string
        """
        job_id = str(job_id) if job_id else str(uuid4())

        message = {
            "job_id": job_id,
            "job_type": job_type,
            "payload": json.dumps(payload),
            "priority": str(priority),
        }

        await self.redis.xadd(self.stream_name, message)
        logger.info(f"Enqueued job {job_id}: {job_type}")

        return job_id

    async def consume(
        self,
        consumer_name: str,
        count: int = 1,
        block_ms: int = 5000,
    ) -> AsyncIterator[dict[str, Any]]:
        """Consume jobs from the queue.

        Args:
            consumer_name: Unique name for this consumer
            count: Max number of jobs to fetch at once
            block_ms: How long to block waiting for jobs

        Yields:
            Job dictionaries with id, job_type, and payload
        """
        await self.ensure_group()

        while True:
            try:
                # First, try to claim any pending messages that are stale
                await self.claim_stale(consumer_name)

                # Read new messages
                messages = await self.redis.xreadgroup(
                    self.group_name,
                    consumer_name,
                    {self.stream_name: ">"},
                    count=count,
                    block=block_ms,
                )

                if not messages:
                    continue

                for stream, stream_messages in messages:
                    for message_id, data in stream_messages:
                        job = {
                            "id": message_id,
                            "job_id": data.get("job_id"),
                            "job_type": data.get("job_type"),
                            "payload": json.loads(data.get("payload", "{}")),
                            "priority": int(data.get("priority", 100)),
                        }
                        yield job

            except Exception as e:
                logger.error(f"Error consuming jobs: {e}")
                # Brief pause before retrying
                import asyncio
                await asyncio.sleep(1)

    async def acknowledge(self, message_id: str) -> None:
        """Acknowledge job completion.

        Args:
            message_id: The stream message ID to acknowledge
        """
        await self.redis.xack(self.stream_name, self.group_name, message_id)
        logger.debug(f"Acknowledged job: {message_id}")

    async def claim_stale(
        self,
        consumer_name: str,
        min_idle_time: timedelta = timedelta(minutes=5),
        count: int = 10,
    ) -> list[str]:
        """Claim stale pending messages from other consumers.

        Args:
            consumer_name: Name of consumer claiming the messages
            min_idle_time: Minimum idle time before claiming
            count: Maximum messages to claim

        Returns:
            List of claimed message IDs
        """
        try:
            claimed = await self.redis.xautoclaim(
                self.stream_name,
                self.group_name,
                consumer_name,
                min_idle_time=int(min_idle_time.total_seconds() * 1000),
                start_id="0-0",
                count=count,
            )

            if claimed and claimed[1]:  # claimed[1] is the list of messages
                message_ids = [msg[0] for msg in claimed[1]]
                if message_ids:
                    logger.info(f"Claimed {len(message_ids)} stale messages")
                return message_ids
            return []
        except Exception as e:
            logger.error(f"Error claiming stale messages: {e}")
            return []

    async def publish_progress(
        self,
        job_id: UUID | str,
        progress: int,
        message: Optional[str] = None,
    ) -> None:
        """Publish job progress via pub/sub.

        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
            message: Optional progress message
        """
        await publish_job_progress(job_id, progress, message)

    async def publish_complete(
        self,
        job_id: UUID | str,
        result: Optional[dict[str, Any]] = None,
    ) -> None:
        """Publish job completion via pub/sub.

        Args:
            job_id: Job ID
            result: Optional result data
        """
        await publish_job_complete(job_id, result)

    async def publish_error(
        self,
        job_id: UUID | str,
        error: str,
    ) -> None:
        """Publish job error via pub/sub.

        Args:
            job_id: Job ID
            error: Error message
        """
        await publish_job_error(job_id, error)


async def create_job_queue(
    stream_name: str = STREAM_NAME,
    group_name: str = GROUP_NAME,
) -> JobQueue:
    """Create a job queue with the current Redis connection.

    Args:
        stream_name: Name of the Redis stream
        group_name: Name of the consumer group

    Returns:
        JobQueue instance
    """
    redis = await get_redis()
    return JobQueue(redis, stream_name, group_name)
