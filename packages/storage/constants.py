"""Constants for storage services.

Defines storage provider names and other storage-related constants
to ensure consistency across the application.
"""

from typing import Final


class StorageProvider:
    """Storage provider constants."""

    GCP: Final[str] = "gcp"
    AWS: Final[str] = "aws"
    AZURE: Final[str] = "azure"

    # List of all supported providers
    ALL: Final[list[str]] = [GCP, AWS, AZURE]

    # Currently implemented providers
    IMPLEMENTED: Final[list[str]] = [GCP]

    # Default provider
    DEFAULT: Final[str] = GCP


class StorageConstants:
    """General storage constants."""

    # Default signed URL expiration (in hours)
    DEFAULT_SIGNED_URL_EXPIRATION_HOURS: Final[int] = 1

    # Maximum file size (100MB in bytes)
    MAX_FILE_SIZE_BYTES: Final[int] = 100 * 1024 * 1024

    # Default GCP location
    DEFAULT_GCP_LOCATION: Final[str] = "us-central1"

    # Default AWS region
    DEFAULT_AWS_REGION: Final[str] = "us-east-1"

    # Storage path prefixes
    FILES_PREFIX: Final[str] = "files/"
    THUMBNAILS_PREFIX: Final[str] = "thumbnails/"

    # Common MIME types
    MIME_TYPES: Final[dict[str, str]] = {
        ".pdf": "application/pdf",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".csv": "text/csv",
        ".txt": "text/plain",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
    }
