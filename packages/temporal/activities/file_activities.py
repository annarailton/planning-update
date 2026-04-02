"""File processing activities.

⚠️  DEMO IMPLEMENTATION - These activities contain placeholder logic for demonstration.
    Replace the simulated sleeps and placeholder returns with actual implementations
    before using in production. See TODO comments in each activity for guidance.

These activities handle individual steps of file processing workflows.
Each activity is independently retryable and can be monitored.

Activities publish progress to Redis for real-time SSE streaming.

Usage in workflows:
    result = await workflow.execute_activity(
        download_file,
        DownloadFileInput(file_id="...", bucket_name="..."),
        start_to_close_timeout=timedelta(minutes=5),
        retry_policy=RetryPolicy(maximum_attempts=3),
    )
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Optional

from temporalio import activity
from temporalio.common import RetryPolicy

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Retry Policies
# ─────────────────────────────────────────────────────────────────────────────

# Fast operations (DB, cache)
FAST_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=3,
)

# Network operations (downloads, API calls)
NETWORK_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    maximum_interval=timedelta(minutes=1),
    maximum_attempts=5,
)

# Heavy operations (encoding, analysis)
HEAVY_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    maximum_interval=timedelta(minutes=10),
    maximum_attempts=3,
)


# ─────────────────────────────────────────────────────────────────────────────
# Progress Publishing Activity
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class PublishProgressInput:
    """Input for publish_progress activity."""

    workflow_id: str
    progress: int
    message: str
    activity_name: Optional[str] = None
    step: Optional[int] = None
    total_steps: Optional[int] = None


@activity.defn
async def publish_progress(input: PublishProgressInput) -> bool:
    """Publish workflow progress to Redis for SSE streaming.

    This activity publishes progress updates that can be streamed
    to frontend clients via SSE.

    Args:
        input: Progress details to publish

    Returns:
        True if published successfully
    """
    try:
        from packages.temporal.progress import publish_workflow_progress

        await publish_workflow_progress(
            workflow_id=input.workflow_id,
            progress=input.progress,
            message=input.message,
            activity=input.activity_name,
            step=input.step,
            total_steps=input.total_steps,
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to publish progress: {e}")
        return False


@dataclass
class PublishCompleteInput:
    """Input for publish_complete activity."""

    workflow_id: str
    result: Optional[dict[str, Any]] = None


@activity.defn
async def publish_complete(input: PublishCompleteInput) -> bool:
    """Publish workflow completion to Redis for SSE streaming.

    Args:
        input: Completion details

    Returns:
        True if published successfully
    """
    try:
        from packages.temporal.progress import publish_workflow_complete

        await publish_workflow_complete(
            workflow_id=input.workflow_id,
            result=input.result,
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to publish completion: {e}")
        return False


@dataclass
class PublishErrorInput:
    """Input for publish_error activity."""

    workflow_id: str
    error: str


@activity.defn
async def publish_error(input: PublishErrorInput) -> bool:
    """Publish workflow error to Redis for SSE streaming.

    Args:
        input: Error details

    Returns:
        True if published successfully
    """
    try:
        from packages.temporal.progress import publish_workflow_error

        await publish_workflow_error(
            workflow_id=input.workflow_id,
            error=input.error,
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to publish error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Activity Input/Output Types
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class DownloadFileInput:
    """Input for download_file activity."""

    file_id: str
    bucket_name: str
    gcs_path: str


@dataclass
class DownloadFileOutput:
    """Output from download_file activity."""

    local_path: str
    size_bytes: int


@dataclass
class CalculateHashInput:
    """Input for calculate_hash activity."""

    local_path: str


@dataclass
class CalculateHashOutput:
    """Output from calculate_hash activity."""

    content_hash: str
    algorithm: str = "sha256"


@dataclass
class ExtractMetadataInput:
    """Input for extract_metadata activity."""

    local_path: str
    file_type: str


@dataclass
class ExtractMetadataOutput:
    """Output from extract_metadata activity."""

    metadata: dict[str, Any]


@dataclass
class GenerateThumbnailInput:
    """Input for generate_thumbnail activity."""

    local_path: str
    output_path: str
    width: int = 256
    height: int = 256


@dataclass
class GenerateThumbnailOutput:
    """Output from generate_thumbnail activity."""

    thumbnail_path: str
    width: int
    height: int


@dataclass
class UpdateFileStatusInput:
    """Input for update_file_status activity."""

    file_id: str
    status: str
    content_hash: Optional[str] = None
    thumbnail_url: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None


@dataclass
class UpdateFileStatusOutput:
    """Output from update_file_status activity."""

    success: bool


# ─────────────────────────────────────────────────────────────────────────────
# Activities
# ─────────────────────────────────────────────────────────────────────────────


@activity.defn
async def download_file(input: DownloadFileInput) -> DownloadFileOutput:
    """Download a file from cloud storage to local temp directory.

    This is a placeholder implementation. Replace with actual GCS download logic.

    Args:
        input: Download parameters including file_id and bucket

    Returns:
        Local path and file size
    """
    logger.info(f"Downloading file {input.file_id} from {input.bucket_name}")

    # TODO: Implement actual download logic
    # Example:
    # from packages.storage import create_storage_service
    # storage = create_storage_service()
    # local_path = await storage.download_to_temp(input.bucket_name, input.gcs_path)

    # Heartbeat for long-running downloads
    activity.heartbeat(f"Downloading {input.file_id}")

    # Simulate processing time for demo
    await asyncio.sleep(1.5)

    # Placeholder return
    return DownloadFileOutput(
        local_path=f"/tmp/{input.file_id}",
        size_bytes=0,
    )


@activity.defn
async def calculate_hash(input: CalculateHashInput) -> CalculateHashOutput:
    """Calculate SHA256 hash of a file for deduplication.

    Args:
        input: Path to the local file

    Returns:
        Content hash using SHA256
    """
    logger.info(f"Calculating hash for {input.local_path}")

    # TODO: Implement actual hash calculation
    # Example:
    # sha256 = hashlib.sha256()
    # with open(input.local_path, 'rb') as f:
    #     for chunk in iter(lambda: f.read(8192), b''):
    #         sha256.update(chunk)
    # return CalculateHashOutput(content_hash=sha256.hexdigest())

    # Simulate processing time for demo
    await asyncio.sleep(1.0)

    # Placeholder return
    return CalculateHashOutput(
        content_hash="placeholder_hash",
        algorithm="sha256",
    )


@activity.defn
async def extract_metadata(input: ExtractMetadataInput) -> ExtractMetadataOutput:
    """Extract metadata from a file (dimensions, duration, etc.).

    Args:
        input: Path to file and its type

    Returns:
        Extracted metadata dictionary
    """
    logger.info(f"Extracting metadata from {input.local_path}")

    # TODO: Implement actual metadata extraction
    # Example for images:
    # from PIL import Image
    # with Image.open(input.local_path) as img:
    #     metadata = {"width": img.width, "height": img.height, "format": img.format}

    # Simulate processing time for demo
    await asyncio.sleep(1.0)

    # Placeholder return
    return ExtractMetadataOutput(
        metadata={
            "file_type": input.file_type,
            "extracted": True,
        }
    )


@activity.defn
async def generate_thumbnail(input: GenerateThumbnailInput) -> GenerateThumbnailOutput:
    """Generate a thumbnail for an image or video.

    Args:
        input: Source path and thumbnail dimensions

    Returns:
        Path to generated thumbnail
    """
    logger.info(f"Generating thumbnail for {input.local_path}")

    # Heartbeat for long-running thumbnail generation
    activity.heartbeat(f"Generating thumbnail")

    # TODO: Implement actual thumbnail generation
    # Example:
    # from PIL import Image
    # with Image.open(input.local_path) as img:
    #     img.thumbnail((input.width, input.height))
    #     img.save(input.output_path)

    # Simulate processing time for demo
    await asyncio.sleep(1.5)

    # Placeholder return
    return GenerateThumbnailOutput(
        thumbnail_path=input.output_path,
        width=input.width,
        height=input.height,
    )


@activity.defn
async def update_file_status(input: UpdateFileStatusInput) -> UpdateFileStatusOutput:
    """Update file status in the database.

    Args:
        input: File ID and new status information

    Returns:
        Success indicator
    """
    logger.info(f"Updating file {input.file_id} status to {input.status}")

    # TODO: Implement actual database update
    # Example:
    # from packages.db import get_db, File
    # async with get_db() as db:
    #     file = await db.get(File, input.file_id)
    #     file.status = input.status
    #     file.content_hash = input.content_hash
    #     await db.commit()

    # Simulate processing time for demo
    await asyncio.sleep(0.5)

    # Placeholder return
    return UpdateFileStatusOutput(success=True)
