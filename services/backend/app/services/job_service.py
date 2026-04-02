"""Job service for orchestrating job operations.

Thin orchestration layer that combines:
- JobRepository for database operations
- JobQueue for Redis Stream operations
"""

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from packages.db import Job
from services.job_repository import JobRepository
from services.job_queue import JobQueue

logger = logging.getLogger(__name__)


class JobService:
    """Service for job orchestration."""

    def __init__(self, repository: JobRepository, queue: JobQueue):
        """Initialize with repository and queue.

        Args:
            repository: Job repository for DB operations
            queue: Job queue for Redis operations
        """
        self.repository = repository
        self.queue = queue

    async def create_and_enqueue(
        self,
        db: AsyncSession,
        job_type: str,
        payload: dict[str, Any],
        user_id: Optional[UUID] = None,
        priority: int = 100,
        max_attempts: int = 3,
    ) -> Job:
        """Create a job and enqueue it for processing.

        Args:
            db: Database session
            job_type: Type of job
            payload: Job payload/arguments
            user_id: Optional user who triggered the job
            priority: Job priority (lower = higher)
            max_attempts: Maximum retry attempts

        Returns:
            Created Job instance
        """
        # 1. Create job in database
        job = await self.repository.create(
            db=db,
            job_type=job_type,
            payload=payload,
            user_id=user_id,
            priority=priority,
            max_attempts=max_attempts,
        )

        # 2. Enqueue to Redis Stream
        await self.queue.enqueue(
            job_id=str(job.id),
            job_type=job_type,
            payload=payload,
        )

        return job

    async def get_job(self, db: AsyncSession, job_id: UUID) -> Optional[Job]:
        """Get a job by ID.

        Args:
            db: Database session
            job_id: Job ID

        Returns:
            Job instance or None if not found
        """
        return await self.repository.get_by_id(db, job_id)

    async def get_user_jobs(
        self,
        db: AsyncSession,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Job]:
        """Get jobs for a user.

        Args:
            db: Database session
            user_id: User ID
            limit: Maximum jobs to return
            offset: Number of jobs to skip

        Returns:
            List of Job instances
        """
        return await self.repository.get_by_user(db, user_id, limit, offset)


def create_job_service(repository: JobRepository, queue: JobQueue) -> JobService:
    """Create a JobService instance.

    Args:
        repository: Job repository
        queue: Job queue

    Returns:
        JobService instance
    """
    return JobService(repository, queue)
