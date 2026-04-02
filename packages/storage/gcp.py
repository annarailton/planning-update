"""Google Cloud Storage implementation.

Provides GCP-specific implementation of the BaseStorageService interface
using the google-cloud-storage SDK.
"""

import json
import logging
import os
from datetime import timedelta
from typing import Any

from google.cloud import storage
from google.cloud.exceptions import Forbidden, NotFound
from google.oauth2 import service_account

from .base import (
    BaseStorageService,
    StorageError,
    StorageNotFoundError,
    StoragePermissionError,
)
from .constants import StorageConstants

logger = logging.getLogger(__name__)


class GCPStorageService(BaseStorageService):
    """Google Cloud Storage implementation."""

    def __init__(self, project_id: str | None = None):
        """Initialize GCP storage service.

        Supports two modes:
        1. Cloud Run with Application Default Credentials
        2. Local development with GOOGLE_SERVICE_ACCOUNT_JSON

        Args:
            project_id: GCP project ID, or None to use environment variable
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID", "test-project")

        try:
            service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
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

            logger.info(f"GCPStorageService initialized for project: {self.project_id}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
            raise RuntimeError(f"Invalid service account JSON: {e}") from e
        except Exception as e:
            logger.error(f"Failed to initialize GCP credentials: {e}")
            raise RuntimeError(f"GCP authentication failed: {e}") from e

    async def upload_file(
        self,
        bucket_name: str,
        file_path: str,
        data: bytes,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Upload file data to GCS bucket."""
        try:
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(file_path)

            blob.upload_from_string(
                data, content_type=content_type or "application/octet-stream"
            )

            if metadata:
                blob.metadata = metadata
                blob.patch()

            logger.info(f"Uploaded {len(data)} bytes to gs://{bucket_name}/{file_path}")
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
            raise StorageNotFoundError(
                f"File not found: gs://{bucket_name}/{file_path}"
            ) from e
        except Forbidden as e:
            raise StoragePermissionError(f"Permission denied: {e}") from e
        except StorageNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to download file from GCS: {e}")
            raise StorageError(f"Download failed: {e}") from e

    async def delete_file(self, bucket_name: str, file_path: str) -> bool:
        """Delete file from GCS bucket."""
        try:
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
            raise StoragePermissionError(f"Permission denied: {e}") from e
        except Exception as e:
            logger.error(f"Failed to delete file from GCS: {e}")
            raise StorageError(f"Delete failed: {e}") from e

    async def file_exists(self, bucket_name: str, file_path: str) -> bool:
        """Check if file exists in GCS bucket."""
        try:
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(file_path)
            exists = blob.exists()
            logger.debug(f"File exists check: gs://{bucket_name}/{file_path} = {exists}")
            return exists
        except Exception as e:
            logger.error(f"Failed to check file existence in GCS: {e}")
            return False

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
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(file_path)

            kwargs: dict[str, Any] = {
                "version": "v4",
                "expiration": expiration,
                "method": method,
            }

            if method == "PUT" and content_type:
                kwargs["content_type"] = content_type
                kwargs["headers"] = {"Content-Type": content_type}

            url = blob.generate_signed_url(**kwargs)

            logger.info(
                f"Generated signed URL for gs://{bucket_name}/{file_path} "
                f"({method}, expires in {expiration})"
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
                f"Listed {len(file_paths)} files in gs://{bucket_name} "
                f"(prefix={prefix}, limit={limit})"
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
                f"Created bucket {bucket_name} in "
                f"{location or StorageConstants.DEFAULT_GCP_LOCATION}"
            )
            return True
        except Forbidden as e:
            raise StoragePermissionError(f"Permission denied: {e}") from e
        except Exception as e:
            logger.error(f"Failed to create GCS bucket: {e}")
            raise StorageError(f"Bucket creation failed: {e}") from e

    async def bucket_exists(self, bucket_name: str) -> bool:
        """Check if GCS bucket exists."""
        try:
            bucket = self._client.bucket(bucket_name)
            exists = bucket.exists()
            logger.debug(f"Bucket exists check: {bucket_name} = {exists}")
            return exists
        except Exception as e:
            logger.error(f"Failed to check bucket existence in GCS: {e}")
            return False
