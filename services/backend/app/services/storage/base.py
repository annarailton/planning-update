"""Abstract base class for cloud storage services.

Defines the interface that all storage providers must implement,
ensuring consistent behavior across different cloud providers.
"""

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any, Optional

from core.exceptions import AppError


class StorageError(AppError):
    """Base exception for storage operations.

    Raises HTTP 500 Internal Server Error.

    Usage:
        raise StorageError("Failed to upload file")
        raise StorageError("GCS connection failed", detail={"bucket": bucket_name})
    """

    def __init__(self, message: str, detail: Optional[Any] = None):
        super().__init__(message=message, detail=detail, status_code=500)


class StorageNotFoundError(StorageError):
    """Raised when a file or bucket is not found.

    Raises HTTP 404 Not Found.

    Usage:
        raise StorageNotFoundError(f"File not found: {file_path}")
    """

    def __init__(self, message: str, detail: Optional[Any] = None):
        super().__init__(message=message, detail=detail)
        self.status_code = 404


class StoragePermissionError(StorageError):
    """Raised when there are insufficient permissions.

    Raises HTTP 403 Forbidden.

    Usage:
        raise StoragePermissionError(f"Permission denied for bucket: {bucket_name}")
    """

    def __init__(self, message: str, detail: Optional[Any] = None):
        super().__init__(message=message, detail=detail)
        self.status_code = 403


class BaseStorageService(ABC):
    """Abstract base class for cloud storage services.

    All storage providers (GCP, AWS, Azure) must implement this interface
    to ensure consistent behavior across the application.
    """

    @abstractmethod
    async def upload_file(
        self,
        bucket_name: str,
        file_path: str,
        data: bytes,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
        return_prefixed_path: bool = True,
    ) -> str:
        """Upload file data to cloud storage.

        Args:
            bucket_name: Name of the storage bucket
            file_path: Full path within the bucket (e.g., "reports/2024/Q1/report.pdf")
            data: File content as bytes
            content_type: MIME type (e.g., "application/pdf")
            metadata: Additional metadata to store with the file
            return_prefixed_path: If True, returns the actual prefixed path used in storage

        Returns:
            The actual storage path (with environment prefix if applicable)

        Raises:
            StorageError: If upload fails
            StoragePermissionError: If insufficient permissions
        """
        pass

    @abstractmethod
    async def download_file(self, bucket_name: str, file_path: str) -> bytes:
        """Download file content as bytes.

        Args:
            bucket_name: Name of the storage bucket
            file_path: Full path within the bucket

        Returns:
            File content as bytes

        Raises:
            StorageNotFoundError: If file doesn't exist
            StoragePermissionError: If insufficient permissions
            StorageError: If download fails
        """
        pass

    @abstractmethod
    async def delete_file(self, bucket_name: str, file_path: str) -> bool:
        """Delete a file from cloud storage.

        Args:
            bucket_name: Name of the storage bucket
            file_path: Full path within the bucket

        Returns:
            True if file was deleted, False if file didn't exist

        Raises:
            StoragePermissionError: If insufficient permissions
            StorageError: If deletion fails
        """
        pass

    @abstractmethod
    async def file_exists(self, bucket_name: str, file_path: str) -> bool:
        """Check if a file exists in cloud storage.

        Args:
            bucket_name: Name of the storage bucket
            file_path: Full path within the bucket

        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
    async def get_file_info(self, bucket_name: str, file_path: str) -> dict[str, Any]:
        """Get file metadata and information.

        Args:
            bucket_name: Name of the storage bucket
            file_path: Full path within the bucket

        Returns:
            Dictionary containing file metadata (size, content_type, etc.)

        Raises:
            StorageNotFoundError: If file doesn't exist
        """
        pass

    @abstractmethod
    async def generate_signed_url(
        self,
        bucket_name: str,
        file_path: str,
        expiration: timedelta = timedelta(hours=1),
        method: str = "GET",
        content_type: str | None = None,
    ) -> str:
        """Generate a signed URL for temporary file access.

        Args:
            bucket_name: Name of the storage bucket
            file_path: Full path within the bucket
            expiration: How long the URL should be valid
            method: HTTP method (GET for download, PUT for upload)

        Returns:
            Signed URL string

        Raises:
            StorageNotFoundError: If file doesn't exist (for GET URLs)
            StorageError: If URL generation fails
        """
        pass

    @abstractmethod
    async def list_files(
        self, bucket_name: str, prefix: str | None = None, limit: int | None = None
    ) -> list[str]:
        """List files in a bucket or directory.

        Args:
            bucket_name: Name of the storage bucket
            prefix: Directory prefix to filter by (e.g., "reports/2024/")
            limit: Maximum number of files to return

        Returns:
            List of file paths
        """
        pass

    @abstractmethod
    async def create_bucket(
        self, bucket_name: str, location: str | None = None
    ) -> bool:
        """Create a new storage bucket.

        Args:
            bucket_name: Name for the new bucket
            location: Cloud region/location for the bucket

        Returns:
            True if bucket was created, False if it already existed

        Raises:
            StoragePermissionError: If insufficient permissions
            StorageError: If creation fails
        """
        pass

    @abstractmethod
    async def bucket_exists(self, bucket_name: str) -> bool:
        """Check if a bucket exists.

        Args:
            bucket_name: Name of the bucket to check

        Returns:
            True if bucket exists, False otherwise
        """
        pass

    @abstractmethod
    def get_prefixed_path(self, file_path: str) -> str:
        """Get the environment-prefixed path for a given file path.

        Storage providers should implement this to handle their specific
        path organization strategy (e.g., environment-based prefixing).

        Args:
            file_path: The base file path (e.g., "files/original/doc.pdf")

        Returns:
            The path with appropriate prefix (e.g., "dev-darryl/files/original/doc.pdf")
        """
        pass
