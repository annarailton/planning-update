"""Worker service main application.

Runs two parallel processing systems:
1. Redis Stream consumer - for simple, quick jobs
2. Temporal worker - for complex, durable workflows (optional)

Provides:
- /health endpoint for health checks (Cloud Run)
- Background Redis Stream consumer loop
- Background Temporal worker (if enabled)

Note: Health endpoint is available immediately to pass Cloud Run startup probe.
Heavy initialization (DB, Redis, Temporal) runs in background task after app starts.
"""

import asyncio
from contextlib import asynccontextmanager
from enum import Enum

from fastapi import FastAPI
from pydantic import BaseModel

from core.config import get_settings
from packages.logging import setup_logging, get_logger
from processor import init_processor, close_processor

# Configure logging using shared package
settings = get_settings()
setup_logging(log_level=settings.log_level, debug=settings.debug)
logger = get_logger(__name__)


class WorkerStatus(str, Enum):
    """Worker initialization status."""

    STARTING = "starting"
    READY = "ready"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str = "worker"
    ready: bool = False
    redis_streams: bool = True
    temporal: bool = False


# Global state
_worker_status: WorkerStatus = WorkerStatus.STARTING
_init_error: str | None = None
_consumer_task: asyncio.Task | None = None  # Redis Stream consumer
_temporal_task: asyncio.Task | None = None  # Temporal worker
_init_task: asyncio.Task | None = None
_temporal_enabled: bool = False


async def _initialize_worker():
    """Initialize worker in background.

    Starts both Redis Stream consumer and Temporal worker (if enabled).
    """
    global _worker_status, _init_error, _consumer_task, _temporal_task, _temporal_enabled

    try:
        logger.info("Initializing worker connections (DB, Redis)...")

        # Initialize job processor (sets up DB, Redis, queue, repository)
        processor = await init_processor()

        # Start Redis Stream consumer loop
        _consumer_task = asyncio.create_task(processor.run())
        logger.info("Redis Stream consumer started")

        # Initialize Temporal worker (optional)
        try:
            from packages.temporal import is_temporal_enabled, get_temporal_client

            if is_temporal_enabled():
                logger.info("Temporal is enabled, initializing worker...")
                from temporal import create_temporal_worker

                temporal_client = await get_temporal_client()
                temporal_worker = await create_temporal_worker(temporal_client)
                _temporal_task = asyncio.create_task(temporal_worker.run())
                _temporal_enabled = True
                logger.info("Temporal worker started")
            else:
                logger.info("Temporal not enabled - skipping Temporal worker")
        except ImportError as e:
            logger.info(f"Temporal not available (temporalio not installed): {e}")
        except Exception as e:
            # Temporal is optional - log warning but continue
            logger.warning(f"Temporal worker failed to start (non-fatal): {e}")
            logger.warning("Complex workflows will not be processed until Temporal is available")

        _worker_status = WorkerStatus.READY
        logger.info("Worker initialization complete - ready to process jobs")

    except Exception as e:
        _worker_status = WorkerStatus.ERROR
        _init_error = str(e)
        logger.error(f"Worker initialization failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Health endpoint is available immediately.
    Heavy initialization runs in background task.
    """
    global _worker_status, _init_task, _consumer_task, _temporal_task

    logger.info("Starting Worker Service...")

    # Start initialization in background (doesn't block health endpoint)
    _init_task = asyncio.create_task(_initialize_worker())

    yield

    # Shutdown
    logger.info("Shutting down Worker Service...")
    was_ready = _worker_status == WorkerStatus.READY
    _worker_status = WorkerStatus.SHUTTING_DOWN

    # Cancel init task if still running
    if _init_task and not _init_task.done():
        _init_task.cancel()
        try:
            await _init_task
        except asyncio.CancelledError:
            pass

    # Stop processor if it was initialized
    if was_ready:
        try:
            from processor import get_processor

            processor = get_processor()
            await processor.stop()
        except RuntimeError:
            pass  # Processor not initialized

    # Cancel Redis consumer task
    if _consumer_task:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        logger.info("Redis Stream consumer stopped")

    # Cancel Temporal worker task
    if _temporal_task:
        _temporal_task.cancel()
        try:
            await _temporal_task
        except asyncio.CancelledError:
            pass
        logger.info("Temporal worker stopped")

    # Close Temporal client
    try:
        from packages.temporal import is_temporal_enabled, close_temporal_client

        if is_temporal_enabled():
            await close_temporal_client()
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Error closing Temporal client: {e}")

    # Close all connections
    await close_processor()

    logger.info("Worker Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Worker Service",
    description="Redis Stream and Temporal job consumer service",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint for Cloud Run.

    Returns 200 immediately (for startup probe).
    The 'ready' field indicates if worker is fully initialized.
    """
    return HealthResponse(
        status=_worker_status.value,
        ready=_worker_status == WorkerStatus.READY,
        redis_streams=True,  # Always enabled
        temporal=_temporal_enabled,
    )


class WakeupResponse(BaseModel):
    """Wakeup endpoint response."""

    status: str
    message: str


@app.post("/wakeup", response_model=WakeupResponse)
async def wakeup():
    """Wakeup endpoint for HTTP activation.

    Called by the backend when starting Temporal workflows to ensure
    the worker container is running. This enables Cloud Run scale-to-zero
    while still supporting Temporal workflows.

    The endpoint returns immediately - the actual Temporal worker
    initialization happens in the background via the lifespan manager.
    """
    return WakeupResponse(
        status=_worker_status.value,
        message="Worker is active" if _worker_status == WorkerStatus.READY else "Worker is starting",
    )
