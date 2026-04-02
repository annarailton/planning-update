"""Shared storage package for cloud provider abstraction.

This package provides a unified interface for different cloud storage providers
through an abstract base class and factory pattern.

Usage:
    from packages.storage import (
        BaseStorageService,
        GCPStorageService,
        create_storage_service,
        StorageProvider,
        StorageConstants,
    )

    # Create GCP storage service
    storage = create_storage_service(StorageProvider.GCP)

    # Or use directly
    storage = GCPStorageService()

    # Upload file
    await storage.upload_file(bucket, path, data)

    # Generate signed URL
    url = await storage.generate_signed_url(bucket, path)
"""

from .base import (
    BaseStorageService,
    StorageError,
    StorageNotFoundError,
    StoragePermissionError,
)
from .constants import StorageConstants, StorageProvider
from .factory import create_storage_service
from .gcp import GCPStorageService

__all__ = [
    # Base classes
    "BaseStorageService",
    # Exceptions
    "StorageError",
    "StorageNotFoundError",
    "StoragePermissionError",
    # Constants
    "StorageProvider",
    "StorageConstants",
    # Factory
    "create_storage_service",
    # Implementations
    "GCPStorageService",
]
