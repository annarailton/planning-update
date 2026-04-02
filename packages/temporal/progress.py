"""Workflow progress publisher for Redis Pub/Sub.

This module provides utilities to publish workflow progress updates to Redis,
enabling real-time SSE streaming to frontend clients.

Uses the shared packages/redis client for connection management.

Usage in activities:
    from packages.temporal.progress import publish_workflow_progress

    @activity.defn
    async def my_activity(input: MyInput) -> MyOutput:
        await publish_workflow_progress(
            workflow_id="process-file-123",
            progress=50,
            message="Processing...",
            activity="my_activity",
        )
"""

import json
import logging
from typing import Any, Optional

from packages.redis import get_redis_or_none
from packages.redis.pubsub import get_workflow_channel

logger = logging.getLogger(__name__)


async def publish_workflow_progress(
    workflow_id: str,
    progress: int,
    message: str,
    activity: Optional[str] = None,
    step: Optional[int] = None,
    total_steps: Optional[int] = None,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    """Publish workflow progress to Redis for SSE streaming.

    Args:
        workflow_id: The Temporal workflow ID
        progress: Progress percentage (0-100)
        message: Human-readable progress message
        activity: Name of current activity (optional)
        step: Current step number (optional)
        total_steps: Total number of steps (optional)
        extra: Additional data to include (optional)
    """
    redis = get_redis_or_none()
    if not redis:
        logger.debug(f"Redis not initialized, skipping progress publish for {workflow_id}")
        return

    try:
        channel = get_workflow_channel(workflow_id)

        data: dict[str, Any] = {
            "event": "progress",
            "workflowId": workflow_id,
            "progress": min(100, max(0, progress)),
            "message": message,
        }

        if activity:
            data["activity"] = activity
        if step is not None:
            data["step"] = step
        if total_steps is not None:
            data["totalSteps"] = total_steps
        if extra:
            data.update(extra)

        await redis.publish(channel, json.dumps(data))
        logger.debug(f"Published progress {progress}% for workflow {workflow_id}")

    except Exception as e:
        # Don't fail the activity if progress publishing fails
        logger.warning(f"Failed to publish progress for {workflow_id}: {e}")


async def publish_activity_start(
    workflow_id: str,
    activity: str,
    step: Optional[int] = None,
    total_steps: Optional[int] = None,
) -> None:
    """Publish activity start event.

    Args:
        workflow_id: The Temporal workflow ID
        activity: Name of the activity starting
        step: Current step number (optional)
        total_steps: Total number of steps (optional)
    """
    redis = get_redis_or_none()
    if not redis:
        return

    try:
        channel = get_workflow_channel(workflow_id)

        data: dict[str, Any] = {
            "event": "activity",
            "workflowId": workflow_id,
            "activity": activity,
            "status": "started",
            "message": f"Starting {activity}...",
        }

        if step is not None:
            data["step"] = step
        if total_steps is not None:
            data["totalSteps"] = total_steps

        await redis.publish(channel, json.dumps(data))
        logger.debug(f"Activity {activity} started for workflow {workflow_id}")

    except Exception as e:
        logger.warning(f"Failed to publish activity start for {workflow_id}: {e}")


async def publish_activity_complete(
    workflow_id: str,
    activity: str,
    step: Optional[int] = None,
    total_steps: Optional[int] = None,
) -> None:
    """Publish activity completion event.

    Args:
        workflow_id: The Temporal workflow ID
        activity: Name of the activity that completed
        step: Current step number (optional)
        total_steps: Total number of steps (optional)
    """
    redis = get_redis_or_none()
    if not redis:
        return

    try:
        channel = get_workflow_channel(workflow_id)

        data: dict[str, Any] = {
            "event": "activity",
            "workflowId": workflow_id,
            "activity": activity,
            "status": "completed",
            "message": f"Completed {activity}",
        }

        if step is not None:
            data["step"] = step
        if total_steps is not None:
            data["totalSteps"] = total_steps

        await redis.publish(channel, json.dumps(data))
        logger.debug(f"Activity {activity} completed for workflow {workflow_id}")

    except Exception as e:
        logger.warning(f"Failed to publish activity complete for {workflow_id}: {e}")


async def publish_workflow_complete(
    workflow_id: str,
    result: Optional[dict[str, Any]] = None,
) -> None:
    """Publish workflow completion event.

    Args:
        workflow_id: The Temporal workflow ID
        result: Workflow result (optional)
    """
    redis = get_redis_or_none()
    if not redis:
        return

    try:
        channel = get_workflow_channel(workflow_id)

        data: dict[str, Any] = {
            "event": "complete",
            "workflowId": workflow_id,
            "status": "COMPLETED",
            "progress": 100,
            "message": "Workflow completed successfully",
        }

        if result:
            data["result"] = result

        await redis.publish(channel, json.dumps(data))
        logger.info(f"Workflow {workflow_id} completed")

    except Exception as e:
        logger.warning(f"Failed to publish workflow complete for {workflow_id}: {e}")


async def publish_workflow_error(
    workflow_id: str,
    error: str,
) -> None:
    """Publish workflow error event.

    Args:
        workflow_id: The Temporal workflow ID
        error: Error message
    """
    redis = get_redis_or_none()
    if not redis:
        return

    try:
        channel = get_workflow_channel(workflow_id)

        data: dict[str, Any] = {
            "event": "error",
            "workflowId": workflow_id,
            "status": "FAILED",
            "error": error,
            "message": f"Workflow failed: {error}",
        }

        await redis.publish(channel, json.dumps(data))
        logger.warning(f"Workflow {workflow_id} failed: {error}")

    except Exception as e:
        logger.warning(f"Failed to publish workflow error for {workflow_id}: {e}")
