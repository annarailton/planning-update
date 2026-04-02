"""Abstract base class for cloud storage services.

Defines the interface that all storage providers must implement,
ensuring consistent behavior across different cloud providers.
"""

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any


class StorageError(Exception):
    """Base exception for storage operations."""

    pass


class StorageNotFoundError(StorageError):
    """Raised when a file or bucket is not found."""

    pass


class StoragePermissionError(StorageError):
    """Raised when there are insufficient permissions."""

    pass


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
    ) -> str:
        """Upload file data to cloud storage.

        Args:
            bucket_name: Name of the storage bucket
            file_path: Full path within the bucket
            data: File content as bytes
            content_type: MIME type (e.g., "application/pdf")
            metadata: Additional metadata to store with the file

        Returns:
            The storage path

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
            content_type: Content type for PUT requests

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
            prefix: Directory prefix to filter by
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
