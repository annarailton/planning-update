"""Temporal workflow endpoints.

Demo endpoints for triggering and monitoring Temporal workflows.
Supports SSE streaming for real-time workflow progress updates.
"""

import asyncio
import json
import logging
from typing import Annotated, Optional
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

from core.config import Settings, get_settings
from core.dependencies import get_redis
from core.exceptions import (
    NotFoundError,
    ServiceError,
    ServiceUnavailableError,
    UnauthorizedError,
)
from packages.redis.pubsub import get_workflow_channel
from schemas import (
    StartWorkflowRequest,
    StartWorkflowResponse,
    WorkflowInfoResponse,
    WorkflowStatusResponse,
)
from services.temporal_service import TemporalService, get_temporal_service

logger = logging.getLogger(__name__)

# Maximum SSE connection duration (1 hour)
MAX_SSE_DURATION_SECONDS = 3600


def _get_temporal_ui_url(settings: Settings, workflow_id: str | None = None) -> str:
    """Get Temporal UI URL based on environment.

    Local: http://localhost:8233/namespaces/{namespace}/workflows/{workflow_id}
    Cloud: https://cloud.temporal.io/namespaces/{namespace}/workflows/{workflow_id}
    """
    namespace = quote(settings.temporal_namespace, safe="")

    # Check if using Temporal Cloud
    # 1. Has API key explicitly set, OR
    # 2. Namespace looks like Temporal Cloud format (contains account suffix like .xxxxx)
    is_cloud = settings.is_temporal_cloud or "." in settings.temporal_namespace

    if is_cloud:
        base = f"https://cloud.temporal.io/namespaces/{namespace}"
    else:
        base = f"http://localhost:8233/namespaces/{namespace}"

    if workflow_id:
        return f"{base}/workflows/{quote(workflow_id, safe='')}"
    return base


router = APIRouter(prefix="/workflows", tags=["workflows"])


# ─────────────────────────────────────────────────────────────────────────────
# Dependencies
# ─────────────────────────────────────────────────────────────────────────────

TemporalServiceDep = Annotated[TemporalService, Depends(get_temporal_service)]


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/status", response_model=WorkflowStatusResponse)
async def get_temporal_status(temporal: TemporalServiceDep):
    """Check if Temporal is enabled and connected.

    Returns the current status of the Temporal integration.
    """
    if temporal.is_enabled:
        settings = get_settings()
        ui_url = _get_temporal_ui_url(settings)
        return WorkflowStatusResponse(
            enabled=True,
            message=f"Temporal is connected and ready. Visit {ui_url} for the UI.",
            ui_url=ui_url,
        )
    else:
        return WorkflowStatusResponse(
            enabled=False,
            message="Temporal is not available. Check TEMPORAL_ADDRESS environment variable.",
        )


@router.post("/process-file", response_model=StartWorkflowResponse)
async def start_process_file_workflow(
    request: StartWorkflowRequest,
    temporal: TemporalServiceDep,
):
    """Start a demo file processing workflow.

    This demonstrates how to trigger a Temporal workflow from the backend.
    The workflow will:
    1. Download the file (simulated)
    2. Calculate hash
    3. Extract metadata
    4. Generate thumbnail
    5. Update status
    """
    if not temporal.is_enabled:
        raise ServiceUnavailableError("Temporal", "Ensure Temporal is running")

    # Generate IDs if not provided
    file_id = request.file_id or str(uuid4())
    user_id = request.user_id or str(uuid4())

    workflow_id = await temporal.start_process_file_workflow(
        file_id=file_id,
        bucket_name=request.bucket_name,
        user_id=user_id,
    )

    if not workflow_id:
        raise ServiceError("Failed to start workflow")

    settings = get_settings()
    ui_url = _get_temporal_ui_url(settings, workflow_id)
    return StartWorkflowResponse(
        workflow_id=workflow_id,
        message=f"Workflow started. Monitor at {ui_url}",
    )


@router.get("/{workflow_id}", response_model=WorkflowInfoResponse)
async def get_workflow_info(
    workflow_id: str,
    temporal: TemporalServiceDep,
):
    """Get information about a workflow.

    Returns the current status and result (if completed) of a workflow.
    """
    if not temporal.is_enabled:
        raise ServiceUnavailableError("Temporal")

    status = await temporal.get_workflow_status(workflow_id)
    if not status:
        raise NotFoundError("Workflow", workflow_id)

    result = None
    if status.get("status") == "COMPLETED":
        result_data = await temporal.get_workflow_result(workflow_id)
        if result_data:
            result = result_data.get("result")

    return WorkflowInfoResponse(
        workflow_id=workflow_id,
        status=status.get("status"),
        start_time=status.get("start_time"),
        close_time=status.get("close_time"),
        result=result,
    )


@router.get("/{workflow_id}/stream")
async def stream_workflow(
    workflow_id: str,
    temporal: TemporalServiceDep,
    token: Optional[str] = Query(None, description="Auth token (for SSE clients)"),
    redis: Redis = Depends(get_redis),
):
    """Stream workflow updates via Server-Sent Events (SSE).

    Subscribe to real-time updates for a Temporal workflow. Events include:
    - connected: Initial connection with current workflow state
    - progress: Progress updates from activities (0-100%)
    - activity: Activity start/complete notifications
    - complete: Workflow completed successfully
    - error: Workflow failed

    The stream closes automatically when the workflow completes or fails.

    Progress updates are published by Temporal activities via Redis Pub/Sub.
    """
    settings = get_settings()
    if not token and settings.env != "development":
        raise UnauthorizedError("Token required")

    if not temporal.is_enabled:
        raise ServiceUnavailableError("Temporal")

    # Get initial workflow status
    status_info = await temporal.get_workflow_status(workflow_id)
    if not status_info:
        raise NotFoundError("Workflow", workflow_id)

    async def event_generator():
        """Generate SSE events from Redis Pub/Sub and Temporal status."""
        pubsub = redis.pubsub()
        channel = get_workflow_channel(workflow_id)

        try:
            await pubsub.subscribe(channel)
            logger.info(f"SSE client subscribed to {channel}")

            # Send initial state
            initial_data = {
                "event": "connected",
                "workflowId": workflow_id,
                "status": status_info.get("status"),
                "progress": 0,
            }
            yield f"event: connected\ndata: {json.dumps(initial_data)}\n\n"

            # If workflow is already complete, send that and close
            current_status = status_info.get("status")
            if current_status == "COMPLETED":
                result_data = await temporal.get_workflow_result(workflow_id)
                complete_data = {
                    "event": "complete",
                    "workflowId": workflow_id,
                    "status": "COMPLETED",
                    "progress": 100,
                    "result": result_data.get("result") if result_data else None,
                }
                yield f"event: complete\ndata: {json.dumps(complete_data)}\n\n"
                return

            if current_status in ("FAILED", "CANCELED", "TERMINATED", "TIMED_OUT"):
                error_data = {
                    "event": "error",
                    "workflowId": workflow_id,
                    "status": current_status,
                    "error": f"Workflow {current_status.lower()}",
                }
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                return

            # Stream updates from Redis Pub/Sub
            poll_counter = 0
            start_time = asyncio.get_event_loop().time()

            while True:
                # Check max SSE duration
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= MAX_SSE_DURATION_SECONDS:
                    logger.info(f"SSE connection timeout for {workflow_id}")
                    timeout_data = {
                        "event": "timeout",
                        "workflowId": workflow_id,
                        "message": "Connection timeout - please reconnect",
                    }
                    yield f"event: timeout\ndata: {json.dumps(timeout_data)}\n\n"
                    break

                try:
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=5.0,  # Check more frequently for updates
                    )

                    if message is None:
                        # Periodically check workflow status from Temporal
                        poll_counter += 1
                        if poll_counter >= 6:  # Every 30 seconds
                            poll_counter = 0
                            latest_status = await temporal.get_workflow_status(
                                workflow_id
                            )
                            if latest_status:
                                current = latest_status.get("status")
                                if current == "COMPLETED":
                                    result_data = await temporal.get_workflow_result(
                                        workflow_id
                                    )
                                    complete_data = {
                                        "event": "complete",
                                        "workflowId": workflow_id,
                                        "status": "COMPLETED",
                                        "progress": 100,
                                        "result": (
                                            result_data.get("result")
                                            if result_data
                                            else None
                                        ),
                                    }
                                    yield f"event: complete\ndata: {json.dumps(complete_data)}\n\n"
                                    break
                                elif current in (
                                    "FAILED",
                                    "CANCELED",
                                    "TERMINATED",
                                    "TIMED_OUT",
                                ):
                                    error_data = {
                                        "event": "error",
                                        "workflowId": workflow_id,
                                        "status": current,
                                        "error": f"Workflow {current.lower()}",
                                    }
                                    yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                                    break

                        # Send keepalive
                        yield ": keepalive\n\n"
                        continue

                    if message["type"] == "message":
                        try:
                            data = json.loads(message["data"])
                        except json.JSONDecodeError as e:
                            logger.warning(f"Malformed message in {channel}: {e}")
                            continue

                        event_type = data.get("event", "progress")

                        yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

                        # Close stream on terminal events
                        if event_type in ("complete", "error"):
                            logger.info(
                                f"Workflow {workflow_id} {event_type}, closing SSE"
                            )
                            break

                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield ": keepalive\n\n"

        except asyncio.CancelledError:
            logger.info(f"SSE client disconnected from {channel}")
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            except Exception as e:
                logger.warning(f"Error cleaning up pubsub for {channel}: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
