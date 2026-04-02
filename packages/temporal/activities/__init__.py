"""Temporal activities package.

Activities are the building blocks of workflows. They perform the actual work
like database operations, API calls, file processing, etc.

Activities are automatically retried on failure based on retry policies.
"""

from .file_activities import (
    # Progress publishing activities
    publish_progress,
    publish_complete,
    publish_error,
    PublishProgressInput,
    PublishCompleteInput,
    PublishErrorInput,
    # File processing activities
    download_file,
    calculate_hash,
    extract_metadata,
    generate_thumbnail,
    update_file_status,
)

__all__ = [
    # Progress publishing
    "publish_progress",
    "publish_complete",
    "publish_error",
    "PublishProgressInput",
    "PublishCompleteInput",
    "PublishErrorInput",
    # File processing activities
    "download_file",
    "calculate_hash",
    "extract_metadata",
    "generate_thumbnail",
    "update_file_status",
]
