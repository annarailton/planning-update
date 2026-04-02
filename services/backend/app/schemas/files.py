"""File schemas for Temasek POC Backend.

Defines Pydantic models for file-related API requests and responses.
"""

from typing import Any
from uuid import UUID

from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator

from core.config import get_settings


class FileResponse(BaseModel):
    """File response model."""

    id: UUID
    filename: str
    original_filename: str
    bucket_id: UUID
    file_size: int
    content_type: str
    storage_path: str
    created_by_id: UUID
    updated_by_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str

    @classmethod
    def from_file_model(cls, file) -> "FileResponse":
        """Convert File model to FileResponse schema."""
        return cls(
            id=file.id,
            filename=file.filename,
            original_filename=file.original_filename,
            bucket_id=file.bucket_id,
            file_size=file.file_size,
            content_type=file.content_type,
            storage_path=file.storage_path,
            created_by_id=file.created_by_id,
            updated_by_id=file.updated_by_id,
            metadata={},  # File model doesn't have metadata field yet
            created_at=file.created_at.isoformat(),
            updated_at=file.updated_at.isoformat(),
        )


class FileUploadRequest(BaseModel):
    """File upload request model (for form data)."""

    bucket_id: UUID = Field(..., description="ID of the bucket to upload to")
    filename: str | None = Field(None, description="Custom filename (optional)")
    metadata: dict[str, Any] | None = Field(
        default_factory=dict, description="Additional file metadata"
    )

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str | None) -> str | None:
        """Validate filename format and length."""
        if v is None:
            return v

        # Check length
        if len(v) > 255:
            raise ValueError("Filename cannot exceed 255 characters")

        # Check for invalid characters
        invalid_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
        if any(char in v for char in invalid_chars):
            raise ValueError(f"Filename contains invalid characters: {invalid_chars}")

        return v


class FileValidationMixin:
    """Mixin class for file validation logic."""

    @staticmethod
    def validate_file_upload(file: UploadFile) -> None:
        """Validate uploaded file against configuration limits."""
        settings = get_settings()

        # Check file size
        if hasattr(file, "size") and file.size:
            max_size = (
                settings.storage.max_file_size_mb * 1024 * 1024
            )  # Convert MB to bytes
            if file.size > max_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"File size ({file.size} bytes) exceeds maximum allowed size ({max_size} bytes)",
                )

        # Check content type
        if file.content_type:
            allowed_types = _get_allowed_mime_types()
            if file.content_type not in allowed_types:
                raise HTTPException(
                    status_code=415,
                    detail=f"File type '{file.content_type}' is not allowed. Allowed types: {allowed_types[:10]}...",
                )

        # Check file extension
        if file.filename:
            import os

            _, ext = os.path.splitext(file.filename.lower())
            allowed_extensions = _get_allowed_extensions()
            if ext and ext not in allowed_extensions:
                raise HTTPException(
                    status_code=415,
                    detail=f"File extension '{ext}' is not allowed. Allowed extensions: {allowed_extensions[:10]}...",
                )


def _get_allowed_mime_types() -> list[str]:
    """Get list of allowed MIME types."""
    return [
        # Documents
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        # Text files
        "text/plain",
        "text/csv",
        "application/json",
        "application/xml",
        "text/xml",
        # Images
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/bmp",
        # Archives
        "application/zip",
        "application/x-rar-compressed",
        "application/x-7z-compressed",
        # Code files
        "text/javascript",
        "text/css",
        "text/html",
        "application/javascript",
    ]


def _get_allowed_extensions() -> list[str]:
    """Get list of allowed file extensions."""
    return [
        # Documents
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        # Text
        ".txt",
        ".csv",
        ".json",
        ".xml",
        # Images
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".bmp",
        # Archives
        ".zip",
        ".rar",
        ".7z",
        # Code
        ".js",
        ".css",
        ".html",
        ".py",
        ".java",
        ".cpp",
        ".c",
    ]


class FileUpdateRequest(BaseModel):
    """File metadata update request model."""

    filename: str | None = Field(None, description="New filename")
    metadata: dict[str, Any] | None = Field(
        None, description="Metadata to merge with existing"
    )


class FileListResponse(BaseModel):
    """File list response model."""

    files: list[FileResponse]
    total: int
    limit: int
    offset: int


class FileSearchRequest(BaseModel):
    """File search request model."""

    query: str = Field(..., description="Text to search for in filenames")
    bucket_id: UUID | None = Field(
        None, description="Optional bucket ID to limit search"
    )
    content_type: str | None = Field(None, description="Optional content type filter")
    limit: int = Field(default=100, description="Maximum number of results")
    offset: int = Field(default=0, description="Number of results to skip")


class FileStatsResponse(BaseModel):
    """File statistics response model."""

    total_files: int
    total_size_bytes: int
    average_size_bytes: float
    bucket_id: UUID | None = None


class FileDownloadResponse(BaseModel):
    """File download response model."""

    signed_url: str
    expires_in_seconds: int


# Export for easy imports
class FileUploadUrlRequest(BaseModel):
    """Request for generating a presigned upload URL."""

    filename: str = Field(..., description="Name of the file to upload")
    bucket_id: UUID = Field(..., description="Database bucket ID for organizing files")
    content_type: str = Field(..., description="MIME type of the file")
    file_size: int = Field(..., description="Size of the file in bytes")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class FileUploadUrlResponse(BaseModel):
    """Response containing presigned URL and file metadata."""

    upload_url: str = Field(..., description="Presigned URL for uploading the file")
    file_id: UUID = Field(..., description="UUID of the file record")
    storage_path: str = Field(..., description="Path where file will be stored")
    expires_in: int = Field(..., description="URL expiration time in seconds")


# =============================================================================
# Batch Upload Schemas
# =============================================================================


class FileUploadMetadata(BaseModel):
    """Metadata for a single file in a batch upload."""

    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of the file")
    file_size: int = Field(..., description="Size of the file in bytes")


class BatchFileUploadUrlRequest(BaseModel):
    """Request for generating multiple presigned upload URLs."""

    bucket_id: UUID = Field(..., description="Database bucket ID for organizing files")
    files: list[FileUploadMetadata] = Field(
        ..., description="List of files to get upload URLs for"
    )


class BatchFileUploadUrlResponseItem(BaseModel):
    """Response item for a single file in batch upload."""

    index: int = Field(..., description="Index of this file in the request")
    upload_url: str = Field(..., description="Presigned URL for uploading the file")
    file_id: UUID = Field(..., description="UUID of the file record")
    storage_path: str = Field(..., description="Path where file will be stored")


class BatchFileUploadUrlResponse(BaseModel):
    """Response containing presigned URLs for batch upload."""

    files: list[BatchFileUploadUrlResponseItem] = Field(
        ..., description="List of upload URLs and file IDs"
    )
    expires_in: int = Field(..., description="URL expiration time in seconds")


class BatchConfirmRequest(BaseModel):
    """Request to confirm multiple file uploads."""

    file_ids: list[UUID] = Field(..., description="List of file IDs to confirm")


class BatchConfirmResponseItem(BaseModel):
    """Response item for a single file confirmation."""

    file_id: UUID = Field(..., description="UUID of the file")
    success: bool = Field(..., description="Whether confirmation succeeded")
    status: str = Field(..., description="Final status of the file")


class BatchConfirmResponse(BaseModel):
    """Response for batch upload confirmation."""

    files: list[BatchConfirmResponseItem] = Field(
        ..., description="List of confirmation results"
    )
    confirmed_count: int = Field(
        ..., description="Number of successfully confirmed files"
    )
    failed_count: int = Field(..., description="Number of failed confirmations")


__all__ = [
    "FileResponse",
    "FileUploadRequest",
    "FileUpdateRequest",
    "FileListResponse",
    "FileSearchRequest",
    "FileStatsResponse",
    "FileDownloadResponse",
    "FileUploadUrlRequest",
    "FileUploadUrlResponse",
    "FileValidationMixin",
    # Batch upload
    "FileUploadMetadata",
    "BatchFileUploadUrlRequest",
    "BatchFileUploadUrlResponseItem",
    "BatchFileUploadUrlResponse",
    "BatchConfirmRequest",
    "BatchConfirmResponseItem",
    "BatchConfirmResponse",
]
