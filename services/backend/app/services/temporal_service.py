"""Temporal workflow service.

Provides methods to start and manage Temporal workflows from the backend.
Falls back gracefully when Temporal is not available.

Supports HTTP activation for Cloud Run scale-to-zero: when starting a workflow,
the service will also call the worker's /wakeup endpoint to ensure the worker
container is running and connected to Temporal.
"""

import asyncio
import logging
from typing import Optional
from urllib.parse import urlparse

import httpx

from core.config import get_settings

logger = logging.getLogger(__name__)

# Lock for singleton creation
_service_lock = asyncio.Lock()


class TemporalService:
    """Service for interacting with Temporal workflows."""

    def __init__(self):
        self._client = None
        self._enabled = False
        self._worker_url = get_settings().worker_url

    async def initialize(self) -> bool:
        """Initialize the Temporal client.

        Returns:
            True if Temporal is available, False otherwise
        """
        try:
            from packages.temporal import is_temporal_enabled, get_temporal_client

            if is_temporal_enabled():
                self._client = await get_temporal_client()
                self._enabled = True
                logger.info("Temporal service initialized")
                return True
            else:
                logger.info("Temporal not enabled - workflows will not be available")
                return False
        except ImportError:
            logger.info("temporalio not installed - Temporal features disabled")
            return False
        except Exception as e:
            logger.warning(f"Failed to initialize Temporal client: {e}")
            return False

    @property
    def is_enabled(self) -> bool:
        """Check if Temporal is enabled and connected."""
        return self._enabled

    async def _wakeup_worker(self) -> None:
        """Wake up the worker via HTTP activation.

        This is a fire-and-forget call - we don't wait for initialization
        to complete, just for the container to start responding.
        Cloud Run will keep the container alive while Temporal worker initializes.
        """
        if not self._worker_url or not self._worker_url.strip():
            logger.debug("No worker URL configured - skipping HTTP activation")
            return

        # Validate URL format to prevent SSRF
        parsed = urlparse(self._worker_url)
        if not parsed.scheme or not parsed.netloc:
            logger.warning(f"Invalid worker URL format: {self._worker_url}")
            return

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{self._worker_url}/wakeup")
                response.raise_for_status()
                data = response.json()
                logger.info(f"Worker wakeup: {data.get('message', 'OK')}")
        except httpx.TimeoutException:
            # Timeout is expected if container is cold starting
            logger.info("Worker wakeup timed out (cold start in progress)")
        except httpx.HTTPStatusError as e:
            logger.warning(f"Worker wakeup returned {e.response.status_code}: {e}")
        except Exception as e:
            # Log but don't fail - Temporal will queue the task
            logger.warning(f"Worker wakeup failed (task will be queued): {e}")

    async def start_process_file_workflow(
        self,
        file_id: str,
        bucket_name: str,
        user_id: str,
    ) -> Optional[str]:
        """Start a file processing workflow.

        Args:
            file_id: UUID of the file to process
            bucket_name: GCS bucket name
            user_id: UUID of the user

        Returns:
            Workflow ID if started, None if Temporal not available
        """
        if not self._enabled or not self._client:
            logger.warning("Temporal not available - cannot start workflow")
            return None

        # Wake up worker (fire-and-forget) to ensure it's running
        # This enables scale-to-zero while maintaining workflow responsiveness
        asyncio.create_task(self._wakeup_worker())

        from packages.temporal import (
            ProcessFileWorkflow,
            ProcessFileInput,
            TemporalConfig,
        )

        config = TemporalConfig.from_env()
        workflow_id = f"process-file-{file_id}"

        try:
            await self._client.start_workflow(
                ProcessFileWorkflow.run,
                ProcessFileInput(
                    file_id=file_id,
                    bucket_name=bucket_name,
                    user_id=user_id,
                ),
                id=workflow_id,
                task_queue=config.task_queue,
            )
            logger.info(f"Started workflow {workflow_id}")
            return workflow_id
        except Exception as e:
            logger.error(f"Failed to start workflow: {e}")
            raise

    async def get_workflow_status(self, workflow_id: str) -> Optional[dict]:
        """Get the status of a running workflow.

        Args:
            workflow_id: The workflow ID

        Returns:
            Status dict or None if not found
        """
        if not self._enabled or not self._client:
            return None

        try:
            handle = self._client.get_workflow_handle(workflow_id)
            describe = await handle.describe()
            return {
                "workflow_id": workflow_id,
                "status": describe.status.name,
                "start_time": (
                    describe.start_time.isoformat() if describe.start_time else None
                ),
                "close_time": (
                    describe.close_time.isoformat() if describe.close_time else None
                ),
            }
        except Exception as e:
            logger.error(f"Failed to get workflow status: {e}")
            return None

    async def get_workflow_result(self, workflow_id: str) -> Optional[dict]:
        """Get the result of a completed workflow.

        Args:
            workflow_id: The workflow ID

        Returns:
            Workflow result or None
        """
        if not self._enabled or not self._client:
            return None

        try:
            handle = self._client.get_workflow_handle(workflow_id)
            result = await handle.result()
            return {
                "workflow_id": workflow_id,
                "result": result.__dict__ if hasattr(result, "__dict__") else result,
            }
        except Exception as e:
            logger.error(f"Failed to get workflow result: {e}")
            return None


# Global instance
_temporal_service: Optional[TemporalService] = None


async def get_temporal_service() -> TemporalService:
    """Get or create the Temporal service singleton.

    Uses double-check locking to prevent race conditions.
    """
    global _temporal_service

    # Fast path - already initialized
    if _temporal_service is not None:
        return _temporal_service

    # Slow path - need to initialize with lock
    async with _service_lock:
        # Double-check after acquiring lock
        if _temporal_service is not None:
            return _temporal_service

        _temporal_service = TemporalService()
        await _temporal_service.initialize()
        return _temporal_service
