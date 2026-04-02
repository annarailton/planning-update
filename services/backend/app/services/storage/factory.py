"""Storage service factory for provider selection.

Creates storage service instances based on provider configuration,
enabling easy switching between different cloud providers.
"""

from core.logging import get_logger

from .base import BaseStorageService
from .constants import StorageProvider

logger = get_logger(__name__)


def create_storage_service(
    provider: str = StorageProvider.DEFAULT,
) -> BaseStorageService:
    """Factory function to create storage service based on provider.

    Args:
        provider: Storage provider name (use StorageProvider constants)
                 Defaults to StorageProvider.DEFAULT (gcp)

    Returns:
        Storage service instance for the specified provider

    Raises:
        ValueError: If provider is not supported
        NotImplementedError: If provider is not yet implemented
    """
    provider = provider.lower().strip()

    if provider == StorageProvider.GCP:
        from .gcp_storage import GCPStorageService

        logger.info("Creating GCP storage service")
        return GCPStorageService()

    elif provider == StorageProvider.AWS:
        # Future implementation
        # from .aws_storage import AWSStorageService
        # logger.info("Creating AWS storage service")
        # return AWSStorageService()
        # Note: AWS implementation should handle get_prefixed_path()
        # (can return path unchanged if no environment prefixing needed)
        raise NotImplementedError(
            f"AWS storage service not implemented yet. "
            f"Available providers: {StorageProvider.IMPLEMENTED}"
        )

    elif provider == StorageProvider.AZURE:
        # Future implementation
        # from .azure_storage import AzureStorageService
        # logger.info("Creating Azure storage service")
        # return AzureStorageService()
        raise NotImplementedError(
            f"Azure storage service not implemented yet. "
            f"Available providers: {StorageProvider.IMPLEMENTED}"
        )

    else:
        raise ValueError(
            f"Unknown storage provider: '{provider}'. "
            f"Supported providers: {StorageProvider.ALL}"
        )
