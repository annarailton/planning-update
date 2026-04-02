"""Job processor for consuming and executing jobs.

Thin orchestration layer that combines:
- JobQueue for Redis Stream operations
- JobRepository for database operations

Uses Redis Streams for reliable job queue with:
- Consumer groups for multiple workers
- XACK for job completion
- XAUTOCLAIM for stale job recovery
- Pub/Sub for real-time progress updates
"""

import asyncio
import json
import logging
import os
import socket
from typing import Any
from uuid import UUID

from core.config import get_settings
from core.redis import init_redis, close_redis
from handlers import HANDLERS
from packages.db import init_database, close_database, get_db
from services.job_queue import create_job_queue, JobQueue
from services.job_repository import get_job_repository, JobRepository

logger = logging.getLogger(__name__)


class JobProcessor:
    """Processes jobs from Redis Stream.

    Orchestrates job queue consumption and execution.
    """

    def __init__(
        self,
        queue: JobQueue,
        repository: JobRepository,
        worker_id: str,
    ):
        """Initialize processor with dependencies.

        Args:
            queue: Job queue for Redis operations
            repository: Job repository for DB operations
            worker_id: Unique worker identifier
        """
        self.settings = get_settings()
        self._queue = queue
        self._repository = repository
        self._worker_id = worker_id
        self._running = False

    @property
    def queue(self) -> JobQueue:
        """Get job queue."""
        return self._queue

    async def run(self) -> None:
        """Main worker loop."""
        self._running = True
        logger.info(f"Starting job processing loop (worker_id={self._worker_id})...")

        while self._running:
            try:
                # Claim stale jobs first
                stale_jobs = await self._queue.claim_stale(
                    self._worker_id,
                    self.settings.worker_job_timeout * 1000,
                )
                for entry_id, data in stale_jobs:
                    logger.warning(f"Reclaimed stale job: {entry_id}")
                    await self._process_entry(entry_id, data)

                # Consume new jobs
                jobs = await self._queue.consume(self._worker_id)
                for entry_id, data in jobs:
                    await self._process_entry(entry_id, data)

            except asyncio.CancelledError:
                logger.info("Job processing loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in job processing loop: {e}")
                await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop the processor loop."""
        logger.info("Stopping job processor...")
        self._running = False

    async def _process_entry(self, entry_id: str, data: dict) -> None:
        """Process a single job entry.

        Args:
            entry_id: Redis Stream entry ID
            data: Job data from stream
        """
        job_id = data.get("job_id")
        job_type = data.get("job_type")
        payload_str = data.get("payload", "{}")

        logger.info(f"Processing job {job_id} (type={job_type}, entry={entry_id})")

        try:
            payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str

            # Get handler
            handler = HANDLERS.get(job_type)
            if not handler:
                await self._fail_job(job_id, f"No handler for job type: {job_type}")
                await self._queue.acknowledge(entry_id)
                return

            # Progress callback
            async def on_progress(progress: int | float, message: str | None = None):
                await self._queue.publish_progress(job_id, progress, message)

            # Execute with timeout
            async with asyncio.timeout(self.settings.worker_job_timeout):
                result = await handler(payload, on_progress=on_progress)

            # Success
            await self._complete_job(job_id, result)
            await self._queue.acknowledge(entry_id)
            logger.info(f"Job {job_id} completed successfully")

        except asyncio.TimeoutError:
            await self._fail_job(job_id, f"Job timed out after {self.settings.worker_job_timeout}s")
            await self._queue.acknowledge(entry_id)
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            await self._fail_job(job_id, str(e))
            await self._queue.acknowledge(entry_id)

    async def _complete_job(self, job_id: str, result: Any) -> None:
        """Mark job completed in DB and publish event.

        Args:
            job_id: Job ID
            result: Job result data
        """
        # Publish to SSE subscribers
        await self._queue.publish_complete(job_id, result)

        # Update database
        async for db in get_db():
            await self._repository.mark_completed(db, UUID(job_id), result)
            break

    async def _fail_job(self, job_id: str, error: str) -> None:
        """Mark job failed in DB and publish event.

        Args:
            job_id: Job ID
            error: Error message
        """
        # Publish to SSE subscribers
        await self._queue.publish_error(job_id, error)

        # Update database
        async for db in get_db():
            await self._repository.mark_failed(db, UUID(job_id), error)
            break


# Singleton processor
_processor: JobProcessor | None = None


async def init_processor() -> JobProcessor:
    """Initialize the job processor with all dependencies.

    Returns:
        Initialized JobProcessor instance
    """
    global _processor
    if _processor is not None:
        return _processor

    settings = get_settings()
    worker_id = f"{socket.gethostname()}-{os.getpid()}"

    logger.info(f"Initializing job processor (worker_id={worker_id})...")

    # Initialize database
    await init_database(
        database_url=settings.database_url,
        echo=settings.debug,
    )

    # Initialize Redis
    redis = await init_redis()

    # Create queue and ensure consumer group exists
    queue = create_job_queue(redis)
    await queue.ensure_consumer_group()

    # Get repository
    repository = get_job_repository()

    # Create processor
    _processor = JobProcessor(queue, repository, worker_id)
    logger.info("Job processor initialized")

    return _processor


async def close_processor() -> None:
    """Close processor and all connections."""
    global _processor
    _processor = None

    await close_redis()
    await close_database()
    logger.info("Job processor closed")


def get_processor() -> JobProcessor:
    """Get job processor singleton.

    Returns:
        JobProcessor instance

    Raises:
        RuntimeError: If processor not initialized
    """
    global _processor
    if _processor is None:
        raise RuntimeError("Processor not initialized. Call init_processor() first.")
    return _processor
