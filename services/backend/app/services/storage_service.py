"""Storage service for Temasek POC Backend.

Provides dependency injection wrapper around the storage factory pattern,
following the established service pattern in the application.
"""

from core.config import get_settings
from core.logging import get_logger

from .storage import BaseStorageService, create_storage_service
from .storage.constants import StorageProvider

logger = get_logger(__name__)


def get_storage_service() -> BaseStorageService:
    """Create storage service instance with dependency injection.

    Returns:
        Storage service instance based on configured provider

    Raises:
        RuntimeError: If initialization fails
    """
    try:
        settings = get_settings()
        provider = settings.storage_provider or StorageProvider.DEFAULT
        logger.info(f"Initializing storage service with provider: {provider}")
        storage_service = create_storage_service(provider)
        logger.info(f"Storage service initialized: {type(storage_service).__name__}")
        return storage_service
    except Exception as e:
        logger.error(f"Failed to initialize storage service: {e}")
        raise RuntimeError(f"Storage service initialization failed: {e}") from e
