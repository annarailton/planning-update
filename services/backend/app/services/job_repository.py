"""Job repository for database operations.

Handles all Postgres CRUD operations for jobs.
Pure database layer - no Redis or queue logic.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db import Job

logger = logging.getLogger(__name__)


class JobRepository:
    """Repository for job database operations."""

    async def create(
        self,
        db: AsyncSession,
        job_type: str,
        payload: dict[str, Any],
        user_id: Optional[UUID] = None,
        priority: int = 100,
        max_attempts: int = 3,
    ) -> Job:
        """Create a new job record.

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
        job = Job(
            job_type=job_type,
            payload=payload,
            user_id=user_id,
            priority=priority,
            max_attempts=max_attempts,
            status="pending",
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        logger.info(f"Created job {job.id} (type={job_type})")
        return job

    async def get_by_id(self, db: AsyncSession, job_id: UUID) -> Optional[Job]:
        """Get a job by ID.

        Args:
            db: Database session
            job_id: Job ID

        Returns:
            Job instance or None if not found
        """
        stmt = select(Job).where(Job.id == job_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user(
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
        stmt = (
            select(Job)
            .where(Job.user_id == user_id)
            .order_by(Job.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        db: AsyncSession,
        job_id: UUID,
        status: str,
        result: Optional[dict[str, Any]] = None,
        error_message: Optional[str] = None,
        increment_attempts: bool = False,
    ) -> Optional[Job]:
        """Update job status.

        Args:
            db: Database session
            job_id: Job ID
            status: New status
            result: Optional result data
            error_message: Optional error message
            increment_attempts: Whether to increment attempt count

        Returns:
            Updated Job or None if not found
        """
        job = await self.get_by_id(db, job_id)
        if not job:
            logger.warning(f"Job {job_id} not found for status update")
            return None

        job.status = status
        job.updated_at = datetime.now(timezone.utc)

        if result is not None:
            job.result = result
        if error_message is not None:
            job.error_message = error_message
        if increment_attempts:
            job.attempts += 1

        await db.commit()
        logger.info(f"Updated job {job_id} status to {status}")
        return job

    async def mark_completed(
        self,
        db: AsyncSession,
        job_id: UUID,
        result: dict[str, Any],
    ) -> Optional[Job]:
        """Mark job as completed.

        Args:
            db: Database session
            job_id: Job ID
            result: Result data

        Returns:
            Updated Job or None if not found
        """
        return await self.update_status(db, job_id, "completed", result=result)

    async def mark_failed(
        self,
        db: AsyncSession,
        job_id: UUID,
        error: str,
        max_attempts: int = 3,
    ) -> Optional[Job]:
        """Mark job as failed or pending retry.

        Args:
            db: Database session
            job_id: Job ID
            error: Error message
            max_attempts: Max retry attempts

        Returns:
            Updated Job or None if not found
        """
        job = await self.get_by_id(db, job_id)
        if not job:
            return None

        job.attempts += 1
        job.error_message = error
        job.updated_at = datetime.now(timezone.utc)

        if job.attempts >= max_attempts:
            job.status = "failed"
            logger.error(
                f"Job {job_id} failed permanently after {job.attempts} attempts"
            )
        else:
            job.status = "pending"  # Will be retried
            logger.warning(
                f"Job {job_id} failed, will retry ({job.attempts}/{max_attempts})"
            )

        await db.commit()
        return job


# Singleton instance
_job_repository: Optional[JobRepository] = None


def get_job_repository() -> JobRepository:
    """Get job repository singleton."""
    global _job_repository
    if _job_repository is None:
        _job_repository = JobRepository()
    return _job_repository
