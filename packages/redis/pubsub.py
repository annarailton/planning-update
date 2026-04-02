"""Redis Pub/Sub helpers for real-time events.

Provides channel naming conventions and publish helpers
for job, file, and project events.

Event Format:
    All events are JSON objects with:
    - event: Event type (e.g., "progress", "complete", "error")
    - Additional fields based on event type
"""

import json
import logging
from typing import Any, Optional
from uuid import UUID

from .client import get_redis_or_none, prefix_key

logger = logging.getLogger(__name__)


# =============================================================================
# Channel Generators
# =============================================================================


def get_job_channel(job_id: UUID | str) -> str:
    """Get pub/sub channel for a specific job.

    Args:
        job_id: Job UUID

    Returns:
        Prefixed channel name (e.g., "prod:job:123e4567-e89b...")
    """
    return prefix_key(f"job:{job_id}")


def get_user_files_channel(user_id: UUID | str) -> str:
    """Get pub/sub channel for a user's file events.

    All file events for a user go to one channel (not per-file)
    to allow a single SSE connection per user.

    Args:
        user_id: User UUID

    Returns:
        Prefixed channel name (e.g., "prod:user:123e4567...:files")
    """
    return prefix_key(f"user:{user_id}:files")


def get_project_channel(project_id: UUID | str) -> str:
    """Get pub/sub channel for a project.

    Args:
        project_id: Project UUID

    Returns:
        Prefixed channel name (e.g., "prod:project:123e4567...")
    """
    return prefix_key(f"project:{project_id}")


def get_workflow_channel(workflow_id: str) -> str:
    """Get pub/sub channel for a Temporal workflow.

    Used for streaming workflow progress to frontend via SSE.

    Args:
        workflow_id: Temporal workflow ID

    Returns:
        Prefixed channel name (e.g., "prod:workflow:process-file-123")
    """
    return prefix_key(f"workflow:{workflow_id}")


# =============================================================================
# Job Events
# =============================================================================


async def publish_job_progress(
    job_id: UUID | str,
    progress: int,
    message: Optional[str] = None,
) -> None:
    """Publish job progress event.

    Args:
        job_id: Job UUID
        progress: Progress percentage (0-100)
        message: Optional progress message
    """
    redis = get_redis_or_none()
    if not redis:
        return

    event = {
        "event": "progress",
        "job_id": str(job_id),
        "progress": progress,
    }
    if message:
        event["message"] = message

    try:
        await redis.publish(get_job_channel(job_id), json.dumps(event))
    except Exception as e:
        logger.error(f"Failed to publish job progress: {e}")


async def publish_job_complete(
    job_id: UUID | str,
    result: Optional[dict[str, Any]] = None,
) -> None:
    """Publish job completion event.

    Args:
        job_id: Job UUID
        result: Optional result data
    """
    redis = get_redis_or_none()
    if not redis:
        return

    event = {
        "event": "complete",
        "job_id": str(job_id),
    }
    if result:
        event["result"] = result

    try:
        await redis.publish(get_job_channel(job_id), json.dumps(event))
    except Exception as e:
        logger.error(f"Failed to publish job complete: {e}")


async def publish_job_error(
    job_id: UUID | str,
    error: str,
) -> None:
    """Publish job error event.

    Args:
        job_id: Job UUID
        error: Error message
    """
    redis = get_redis_or_none()
    if not redis:
        return

    event = {
        "event": "error",
        "job_id": str(job_id),
        "error": error,
    }

    try:
        await redis.publish(get_job_channel(job_id), json.dumps(event))
    except Exception as e:
        logger.error(f"Failed to publish job error: {e}")


# =============================================================================
# File Events
# =============================================================================


async def publish_file_status(
    user_id: UUID | str,
    file_id: UUID | str,
    status: str,
    message: Optional[str] = None,
) -> None:
    """Publish file status change event.

    Args:
        user_id: User UUID (for channel routing)
        file_id: File UUID
        status: New status (e.g., "processing", "uploaded")
        message: Optional status message
    """
    redis = get_redis_or_none()
    if not redis:
        return

    event = {
        "event": "status",
        "file_id": str(file_id),
        "status": status,
    }
    if message:
        event["message"] = message

    try:
        await redis.publish(get_user_files_channel(user_id), json.dumps(event))
    except Exception as e:
        logger.error(f"Failed to publish file status: {e}")


async def publish_file_complete(
    user_id: UUID | str,
    file_id: UUID | str,
    thumbnail_url: Optional[str] = None,
    existing_file_id: Optional[UUID | str] = None,
) -> None:
    """Publish file processing complete event.

    Args:
        user_id: User UUID (for channel routing)
        file_id: File UUID
        thumbnail_url: Optional thumbnail URL
        existing_file_id: If duplicate, the ID of existing file
    """
    redis = get_redis_or_none()
    if not redis:
        return

    event: dict[str, Any] = {
        "event": "complete",
        "file_id": str(file_id),
    }
    if thumbnail_url:
        event["thumbnail_url"] = thumbnail_url
    if existing_file_id:
        event["existing_file_id"] = str(existing_file_id)

    try:
        await redis.publish(get_user_files_channel(user_id), json.dumps(event))
    except Exception as e:
        logger.error(f"Failed to publish file complete: {e}")


async def publish_file_error(
    user_id: UUID | str,
    file_id: UUID | str,
    error: str,
) -> None:
    """Publish file processing error event.

    Args:
        user_id: User UUID (for channel routing)
        file_id: File UUID
        error: Error message
    """
    redis = get_redis_or_none()
    if not redis:
        return

    event = {
        "event": "error",
        "file_id": str(file_id),
        "error": error,
    }

    try:
        await redis.publish(get_user_files_channel(user_id), json.dumps(event))
    except Exception as e:
        logger.error(f"Failed to publish file error: {e}")


# =============================================================================
# Project Events
# =============================================================================


async def publish_project_status(
    project_id: UUID | str,
    status: str,
    message: Optional[str] = None,
) -> None:
    """Publish project status change event.

    Args:
        project_id: Project UUID
        status: New status
        message: Optional status message
    """
    redis = get_redis_or_none()
    if not redis:
        return

    event = {
        "event": "status",
        "project_id": str(project_id),
        "status": status,
    }
    if message:
        event["message"] = message

    try:
        await redis.publish(get_project_channel(project_id), json.dumps(event))
    except Exception as e:
        logger.error(f"Failed to publish project status: {e}")


async def publish_project_progress(
    project_id: UUID | str,
    progress: int,
    message: Optional[str] = None,
) -> None:
    """Publish project progress event.

    Args:
        project_id: Project UUID
        progress: Progress percentage (0-100)
        message: Optional progress message
    """
    redis = get_redis_or_none()
    if not redis:
        return

    event = {
        "event": "progress",
        "project_id": str(project_id),
        "progress": progress,
    }
    if message:
        event["message"] = message

    try:
        await redis.publish(get_project_channel(project_id), json.dumps(event))
    except Exception as e:
        logger.error(f"Failed to publish project progress: {e}")


async def publish_project_complete(
    project_id: UUID | str,
    result: Optional[dict[str, Any]] = None,
) -> None:
    """Publish project completion event.

    Args:
        project_id: Project UUID
        result: Optional result data
    """
    redis = get_redis_or_none()
    if not redis:
        return

    event: dict[str, Any] = {
        "event": "complete",
        "project_id": str(project_id),
    }
    if result:
        event["result"] = result

    try:
        await redis.publish(get_project_channel(project_id), json.dumps(event))
    except Exception as e:
        logger.error(f"Failed to publish project complete: {e}")


async def publish_project_error(
    project_id: UUID | str,
    error: str,
) -> None:
    """Publish project error event.

    Args:
        project_id: Project UUID
        error: Error message
    """
    redis = get_redis_or_none()
    if not redis:
        return

    event = {
        "event": "error",
        "project_id": str(project_id),
        "error": error,
    }

    try:
        await redis.publish(get_project_channel(project_id), json.dumps(event))
    except Exception as e:
        logger.error(f"Failed to publish project error: {e}")
