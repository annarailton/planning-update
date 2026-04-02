"""Google Cloud Storage implementation.

Provides GCP-specific implementation of the BaseStorageService interface
using the google-cloud-storage SDK.
"""

import json
from datetime import timedelta
from typing import Any

from google.cloud import storage
from google.cloud.exceptions import Forbidden, NotFound
from google.oauth2 import service_account

from core.logging import get_logger
from core.config import get_settings

from .base import (
    BaseStorageService,
    StorageError,
    StorageNotFoundError,
    StoragePermissionError,
)
from .constants import StorageConstants

logger = get_logger(__name__)


class GCPStorageService(BaseStorageService):
    """Google Cloud Storage implementation."""

    def __init__(self, project_id: str | None = None):
        """Initialize GCP storage service.

        Supports two modes:
        1. Cloud Run with Application Default Credentials
        2. Local development with GOOGLE_SERVICE_ACCOUNT_JSON

        Args:
            project_id: GCP project ID, or None to use settings
        """
        settings = get_settings()
        self.project_id = project_id or settings.gcp_project_id or "test-project"

        try:
            service_account_json = settings.google_service_account_json
            if service_account_json:
                # Local development with service account
                logger.info("Using provided service account credentials")
                service_account_info = json.loads(service_account_json)
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info
                )
                self._client = storage.Client(
                    credentials=credentials, project=self.project_id
                )
            else:
                # Cloud Run with Application Default Credentials
                logger.info("Using Application Default Credentials (Cloud Run)")
                self._client = storage.Client(project=self.project_id)

            # Optional: Set storage prefix if you want to organize files within buckets
            # Since buckets are already environment-specific, prefix is not needed by default
            self.storage_prefix = None

            logger.info(f"GCPStorageService initialized for project: {self.project_id}")
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON")
            raise RuntimeError("Invalid service account JSON configuration") from e
        except Exception as e:
            logger.error(f"Failed to initialize GCP credentials: {type(e).__name__}")
            raise RuntimeError("GCP authentication failed") from e

    def _get_storage_prefix(self) -> str:
        """Get optional storage prefix for file organization.

        Not used by default since buckets are environment-specific.
        Enable by setting self.storage_prefix = self._get_storage_prefix()
        in __init__ if you want to organize files with prefixes.

        Priority:
        1. STORAGE_ENV_PREFIX (explicit override)
        2. K_SERVICE (automatic on Cloud Run)
        3. Simple fallback (local-dev)
        """
        settings = get_settings()

        # 1. Check explicit override first (for local/Docker development)
        if settings.storage_env_prefix:
            logger.info(f"Using explicit storage prefix: {settings.storage_env_prefix}")
            return settings.storage_env_prefix

        # 2. Check if running on Cloud Run (automatic)
        if settings.k_service:
            # t2-backend-staging -> staging
            # t2-backend-prod -> prod
            # t2-backend-dev-darryl -> dev-darryl
            if settings.k_service.startswith("t2-backend-"):
                prefix = settings.k_service.replace("t2-backend-", "")
                # Special case: main branch deploys as 'prod'
                if prefix == "main":
                    prefix = "prod"
                logger.info(f"Detected Cloud Run environment, using prefix: {prefix}")
                return prefix

        # 3. Simple fallback for unspecified environments
        fallback = "local-dev"
        logger.info(
            f"Using fallback prefix: {fallback} (set STORAGE_ENV_PREFIX to customize)"
        )
        return fallback

    def _prepend_prefix(self, file_path: str) -> str:
        """Add optional prefix to file path.

        Currently not used since buckets are environment-specific,
        but available if you want to organize files with prefixes
        (e.g., by user ID, date, or feature).
        """
        if self.storage_prefix:
            return f"{self.storage_prefix}/{file_path}"
        return file_path

    def get_prefixed_path(self, file_path: str) -> str:
        """Get the storage path for a given file path.

        Since buckets are already environment-specific, no prefix is needed.

        Args:
            file_path: The file path (e.g., "doc_20241115_abc123.pdf")

        Returns:
            The same file path (no prefix needed)
        """
        return file_path

    async def upload_file(
        self,
        bucket_name: str,
        file_path: str,
        data: bytes,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
        return_prefixed_path: bool = True,
    ) -> str:
        """Upload file data to GCS bucket.

        Args:
            bucket_name: GCS bucket name
            file_path: Path within bucket (will be auto-prefixed with environment)
            data: File content as bytes
            content_type: MIME type of the file
            metadata: Additional metadata for the file
            return_prefixed_path: If True, returns the actual prefixed path used in GCS
                                 If False, returns the original path (for backward compatibility)

        Returns:
            Either the prefixed path or original path based on return_prefixed_path
        """
        try:
            # No prefix needed - buckets are already environment-specific
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(file_path)

            blob.upload_from_string(
                data, content_type=content_type or "application/octet-stream"
            )

            if metadata:
                blob.metadata = metadata
                blob.patch()

            logger.info(f"Uploaded {len(data)} bytes to gs://{bucket_name}/{file_path}")

            # Always return the file_path as-is (no prefix)
            return file_path
        except NotFound as e:
            logger.error(f"Bucket not found: {bucket_name}")
            raise StorageNotFoundError(f"Bucket not found: {bucket_name}") from e
        except Forbidden as e:
            logger.error(f"Permission denied for bucket: {bucket_name}")
            raise StoragePermissionError(f"Permission denied: {e}") from e
        except Exception as e:
            logger.error(f"Failed to upload file to GCS: {e}")
            raise StorageError(f"Upload failed: {e}") from e

    async def download_file(self, bucket_name: str, file_path: str) -> bytes:
        """Download file from GCS bucket."""
        try:
            # Note: file_path should already include prefix from database
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(file_path)

            if not blob.exists():
                raise StorageNotFoundError(
                    f"File not found: gs://{bucket_name}/{file_path}"
                )

            data = blob.download_as_bytes()
            logger.info(
                f"Downloaded {len(data)} bytes from gs://{bucket_name}/{file_path}"
            )
            return data
        except NotFound as e:
            logger.error(f"File not found: gs://{bucket_name}/{file_path}")
            raise StorageNotFoundError(
                f"File not found: gs://{bucket_name}/{file_path}"
            ) from e
        except Forbidden as e:
            logger.error(f"Permission denied for file: gs://{bucket_name}/{file_path}")
            raise StoragePermissionError(f"Permission denied: {e}") from e
        except StorageNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to download file from GCS: {e}")
            raise StorageError(f"Download failed: {e}") from e

    async def delete_file(self, bucket_name: str, file_path: str) -> bool:
        """Delete file from GCS bucket."""
        try:
            # Note: file_path should already include prefix from database
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(file_path)

            if not blob.exists():
                return False

            blob.delete()
            logger.info(f"Deleted gs://{bucket_name}/{file_path}")
            return True
        except NotFound:
            return False
        except Forbidden as e:
            logger.error(f"Permission denied for file: gs://{bucket_name}/{file_path}")
            raise StoragePermissionError(f"Permission denied: {e}") from e
        except Exception as e:
            logger.error(f"Failed to delete file from GCS: {e}")
            raise StorageError(f"Delete failed: {e}") from e

    async def file_exists(self, bucket_name: str, file_path: str) -> bool:
        """Check if file exists in GCS bucket.

        Raises:
            StoragePermissionError: If permission is denied
            StorageError: If check fails due to network/other errors
        """
        try:
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(file_path)
            exists = blob.exists()

            logger.debug(
                f"File exists check: gs://{bucket_name}/{file_path} = {exists}"
            )
            return exists
        except Forbidden as e:
            logger.error(
                f"Permission denied checking file: gs://{bucket_name}/{file_path}"
            )
            raise StoragePermissionError(f"Permission denied: {e}") from e
        except Exception as e:
            logger.error(f"Failed to check file existence in GCS: {e}")
            raise StorageError(f"File existence check failed: {e}") from e

    async def get_file_info(self, bucket_name: str, file_path: str) -> dict[str, Any]:
        """Get GCS file metadata."""
        try:
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(file_path)

            if not blob.exists():
                raise StorageNotFoundError(
                    f"File not found: gs://{bucket_name}/{file_path}"
                )

            blob.reload()
            return {
                "size": blob.size,
                "content_type": blob.content_type,
                "created": blob.time_created.isoformat() if blob.time_created else None,
                "updated": blob.updated.isoformat() if blob.updated else None,
                "etag": blob.etag,
                "metadata": blob.metadata or {},
            }
        except NotFound as e:
            logger.error(f"File not found: gs://{bucket_name}/{file_path}")
            raise StorageNotFoundError(
                f"File not found: gs://{bucket_name}/{file_path}"
            ) from e
        except StorageNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get file info from GCS: {e}")
            raise StorageError(f"Get file info failed: {e}") from e

    async def generate_signed_url(
        self,
        bucket_name: str,
        file_path: str,
        expiration: timedelta = timedelta(
            hours=StorageConstants.DEFAULT_SIGNED_URL_EXPIRATION_HOURS
        ),
        method: str = "GET",
        content_type: str | None = None,
    ) -> str:
        """Generate GCS signed URL."""
        try:
            # No prefix needed - buckets are already environment-specific
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(file_path)

            # For PUT requests, we need to specify content type
            kwargs = {"version": "v4", "expiration": expiration, "method": method}

            if method == "PUT" and content_type:
                kwargs["content_type"] = content_type
                # Also add headers for CORS
                kwargs["headers"] = {"Content-Type": content_type}

            url = blob.generate_signed_url(**kwargs)

            logger.info(
                f"Generated signed URL for gs://{bucket_name}/{file_path} ({method}, expires in {expiration})"
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed URL for GCS: {e}")
            raise StorageError(f"Signed URL generation failed: {e}") from e

    async def list_files(
        self, bucket_name: str, prefix: str | None = None, limit: int | None = None
    ) -> list[str]:
        """List files in GCS bucket."""
        try:
            bucket = self._client.bucket(bucket_name)
            blobs = bucket.list_blobs(prefix=prefix, max_results=limit)

            file_paths = [blob.name for blob in blobs]

            logger.info(
                f"Listed {len(file_paths)} files in gs://{bucket_name} (prefix={prefix}, limit={limit})"
            )
            return file_paths
        except Exception as e:
            logger.error(f"Failed to list files in GCS: {e}")
            raise StorageError(f"List files failed: {e}") from e

    async def create_bucket(
        self, bucket_name: str, location: str | None = None
    ) -> bool:
        """Create GCS bucket."""
        try:
            bucket = self._client.bucket(bucket_name)
            if bucket.exists():
                logger.info(f"Bucket {bucket_name} already exists")
                return False

            bucket.create(location=location or StorageConstants.DEFAULT_GCP_LOCATION)
            logger.info(
                f"Created bucket {bucket_name} in {location or StorageConstants.DEFAULT_GCP_LOCATION}"
            )
            return True
        except Forbidden as e:
            logger.error(f"Permission denied creating bucket: {bucket_name}")
            raise StoragePermissionError(f"Permission denied: {e}") from e
        except Exception as e:
            logger.error(f"Failed to create GCS bucket: {e}")
            raise StorageError(f"Bucket creation failed: {e}") from e

    async def bucket_exists(self, bucket_name: str) -> bool:
        """Check if GCS bucket exists.

        Raises:
            StoragePermissionError: If permission is denied
            StorageError: If check fails due to network/other errors
        """
        try:
            bucket = self._client.bucket(bucket_name)
            exists = bucket.exists()
            logger.debug(f"Bucket exists check: {bucket_name} = {exists}")
            return exists
        except Forbidden as e:
            logger.error(f"Permission denied checking bucket: {bucket_name}")
            raise StoragePermissionError(f"Permission denied: {e}") from e
        except Exception as e:
            logger.error(f"Failed to check bucket existence in GCS: {e}")
            raise StorageError(f"Bucket existence check failed: {e}") from e
