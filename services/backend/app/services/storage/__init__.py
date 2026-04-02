"""Storage services for cloud provider abstraction.

This package provides a unified interface for different cloud storage providers
through an abstract base class and factory pattern combined with dependency injection.

Usage:
    # For dependency injection
    from services.storage_service import get_storage_service

    # For direct factory usage
    from services.storage import create_storage_service, StorageProvider
"""

from .base import (
    BaseStorageService,
    StorageError,
    StorageNotFoundError,
    StoragePermissionError,
)
from .constants import StorageConstants, StorageProvider
from .factory import create_storage_service

__all__ = [
    "BaseStorageService",
    "StorageError",
    "StorageNotFoundError",
    "StoragePermissionError",
    "create_storage_service",
    "StorageProvider",
    "StorageConstants",
]
