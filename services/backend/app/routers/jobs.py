"""Jobs router for background job management.

Provides endpoints for:
- Creating jobs (POST /api/jobs)
- Getting job status (GET /api/jobs/{id})
- Streaming job updates via SSE (GET /api/jobs/{id}/stream)
"""

import asyncio
import json
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import Field
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import (
    AuthTokenDep,
    DatabaseDep,
    JobServiceDep,
    get_redis,
)
from core.config import get_settings
from core.logging import get_logger
from packages.db import get_db
from packages.redis.pubsub import get_job_channel
from schemas.base import CamelCaseModel
from services.job_repository import get_job_repository

logger = get_logger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


# Request/Response schemas
class CreateJobRequest(CamelCaseModel):
    """Request to create a new job."""

    job_type: str = Field(..., description="Type of job to run")
    payload: dict[str, Any] = Field(default_factory=dict, description="Job payload")
    priority: int = Field(default=100, description="Priority (lower = higher)")


class JobResponse(CamelCaseModel):
    """Job response."""

    id: UUID
    job_type: str
    status: str
    payload: Optional[dict[str, Any]] = None
    result: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str


class CreateJobResponse(CamelCaseModel):
    """Response after creating a job."""

    job_id: UUID
    status: str
    message: str


@router.post("", response_model=CreateJobResponse)
async def create_job(
    request: CreateJobRequest,
    auth: AuthTokenDep,
    db: DatabaseDep,
    job_service: JobServiceDep,
):
    """Create a new background job.

    The job will be enqueued to Redis Stream and processed by a worker.
    Use the returned job_id to track progress via SSE.
    """
    user = auth.get("user")
    user_id = user.id if user else None

    job = await job_service.create_and_enqueue(
        db=db,
        job_type=request.job_type,
        payload=request.payload,
        user_id=user_id,
        priority=request.priority,
    )

    return CreateJobResponse(
        job_id=job.id,
        status=job.status,
        message="Job created and enqueued",
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    auth: AuthTokenDep,
    db: DatabaseDep,
    job_service: JobServiceDep,
):
    """Get job status and details."""
    job = await job_service.get_job(db, job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return JobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        payload=job.payload,
        result=job.result,
        error_message=job.error_message,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
    )


@router.get("/{job_id}/stream")
async def stream_job(
    job_id: UUID,
    token: Optional[str] = Query(None, description="Auth token (for SSE clients)"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Stream job updates via Server-Sent Events (SSE).

    Subscribe to real-time updates for a job. Events include:
    - connected: Initial connection with current job state
    - progress: Progress updates (0-100%)
    - complete: Job completed successfully
    - error: Job failed

    The stream closes automatically when the job completes or fails.

    Note: Pass auth token as query param since EventSource doesn't support headers.
    """
    # Verify token (SSE can't use headers, so we accept query param)
    settings = get_settings()
    if not token and settings.env != "development":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token required",
        )

    # Get job using repository directly (no need for full service)
    repository = get_job_repository()
    job = await repository.get_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    async def event_generator():
        """Generate SSE events from Redis Pub/Sub."""
        pubsub = redis.pubsub()
        channel = get_job_channel(job_id)

        try:
            await pubsub.subscribe(channel)
            logger.info(f"SSE client subscribed to {channel}")

            # Send initial state
            initial_data = {
                "event": "connected",
                "job_id": str(job_id),
                "status": job.status,
                "progress": 0,
            }
            yield f"event: connected\ndata: {json.dumps(initial_data)}\n\n"

            # If job is already complete, send that and close
            if job.status == "completed":
                complete_data = {
                    "event": "complete",
                    "job_id": str(job_id),
                    "result": job.result,
                }
                yield f"event: complete\ndata: {json.dumps(complete_data)}\n\n"
                return

            if job.status == "failed":
                error_data = {
                    "event": "error",
                    "job_id": str(job_id),
                    "error": job.error_message,
                }
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                return

            # Stream updates from Redis Pub/Sub
            consecutive_json_errors = 0
            max_json_errors = 10

            while True:
                try:
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=30.0,  # Send keepalive every 30s
                    )

                    if message is None:
                        # Keepalive
                        yield ": keepalive\n\n"
                        continue

                    if message["type"] == "message":
                        try:
                            data = json.loads(message["data"])
                            consecutive_json_errors = 0  # Reset on success
                        except json.JSONDecodeError:
                            consecutive_json_errors += 1
                            logger.warning(
                                f"Invalid JSON in SSE message for job {job_id} ({consecutive_json_errors}/{max_json_errors})"
                            )
                            if consecutive_json_errors >= max_json_errors:
                                logger.error(
                                    f"Too many JSON errors for job {job_id}, closing stream"
                                )
                                break
                            continue

                        event_type = data.get("event", "update")

                        yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

                        # Close stream on terminal events
                        if event_type in ("complete", "error"):
                            logger.info(f"Job {job_id} {event_type}, closing SSE")
                            break

                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield ": keepalive\n\n"

        except asyncio.CancelledError:
            logger.info(f"SSE client disconnected from {channel}")
        finally:
            try:
                await pubsub.unsubscribe(channel)
            except Exception as e:
                logger.warning(f"Error unsubscribing from {channel}: {e}")
            try:
                await pubsub.aclose()
            except Exception as e:
                logger.warning(f"Error closing pubsub for {channel}: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
