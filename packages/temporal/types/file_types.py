"""Type definitions for file processing workflows.

These dataclasses define the input and output types for
file processing Temporal workflows.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID


@dataclass
class ProcessFileInput:
    """Input for processing a single file.

    Attributes:
        file_id: UUID of the file to process
        bucket_name: Name of the storage bucket
        user_id: UUID of the user who owns the file
    """

    file_id: str
    bucket_name: str
    user_id: str


@dataclass
class ProcessFileOutput:
    """Output from processing a single file.

    Attributes:
        file_id: UUID of the processed file
        status: Final status (available, failed, duplicate)
        content_hash: Hash of file content (for deduplication)
        thumbnail_url: URL of generated thumbnail (if applicable)
        metadata: Extracted file metadata
        existing_file_id: If duplicate, the ID of the existing file
        error_message: Error message if processing failed
    """

    file_id: str
    status: str
    content_hash: Optional[str] = None
    thumbnail_url: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    existing_file_id: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ProcessBatchFilesInput:
    """Input for processing multiple files.

    Files are processed sequentially to avoid race conditions
    in duplicate detection.

    Attributes:
        file_ids: List of file UUIDs to process
        bucket_name: Name of the storage bucket
        user_id: UUID of the user who owns the files
    """

    file_ids: list[str]
    bucket_name: str
    user_id: str


@dataclass
class ProcessBatchFilesOutput:
    """Output from processing multiple files.

    Attributes:
        results: List of individual file results
        total_processed: Number of files successfully processed
        total_duplicates: Number of duplicate files found
        total_failed: Number of files that failed processing
    """

    results: list[ProcessFileOutput] = field(default_factory=list)
    total_processed: int = 0
    total_duplicates: int = 0
    total_failed: int = 0
