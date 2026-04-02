"""Unit tests for Storage Service with mocked GCS dependencies.

Following best practices for mocking GCS at the SDK level using unittest.mock.
"""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from core.config import get_settings
from services.storage.gcp_storage import GCPStorageService
from services.storage.base import (
    StorageError,
    StorageNotFoundError,
    StoragePermissionError,
)


@pytest.fixture
def mock_gcp_environment(monkeypatch):
    """Set up required environment variables for GCP storage service."""

    get_settings.cache_clear()
    monkeypatch.setenv("GCP_PROJECT_ID", "FAKE-TEST-PROJECT")
    monkeypatch.setenv("GCS_BUCKET_NAME", "FAKE-TEST-BUCKET")
    monkeypatch.setenv(
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        json.dumps(
            {
                "type": "service_account",
                "project_id": "FAKE-TEST-PROJECT",
                "private_key_id": "FAKE-KEY-ID-FOR-TESTING",
                "private_key": "-----BEGIN PRIVATE KEY-----\nFAKE-KEY-FOR-TESTING-ONLY\n-----END PRIVATE KEY-----",
                "client_email": "FAKE-TEST@FAKE-TEST-PROJECT.iam.gserviceaccount.com",
                "client_id": "000000000000",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        ),
    )
    monkeypatch.setenv("STORAGE_ENV_PREFIX", "test-env")


@pytest.fixture
def mock_gcs_service(mock_gcp_environment):
    """Create a GCPStorageService with mocked GCS client."""
    with (
        patch(
            "services.storage.gcp_storage.service_account.Credentials.from_service_account_info"
        ) as mock_creds,
        patch("services.storage.gcp_storage.storage.Client") as mock_client_class,
    ):
        # Mock credentials
        mock_creds.return_value = Mock()

        # Mock storage client
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Create service
        service = GCPStorageService()

        # Attach mocks for easy access in tests
        service._mock_client = mock_client
        service._mock_client_class = mock_client_class

        yield service


class TestGCPStorageService:
    """Test GCP Storage Service with mocked Google Cloud Storage."""

    @pytest.mark.asyncio
    async def test_initialization_with_service_account(self, mock_gcs_service):
        """Test initialization with service account credentials."""
        # Service is already initialized via mock_gcs_service fixture
        assert mock_gcs_service.project_id == "FAKE-TEST-PROJECT"

    @pytest.mark.asyncio
    async def test_upload_file_without_prefix_return(self, mock_gcs_service):
        """Test upload returning non-prefixed path."""
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_gcs_service._mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        result = await mock_gcs_service.upload_file(
            bucket_name="test-bucket",
            file_path="uploads/test.txt",
            data=b"content",
            return_prefixed_path=False,
        )

        # Should return original path when return_prefixed_path=False
        assert result == "uploads/test.txt"

    @pytest.mark.asyncio
    async def test_download_file_success(self, mock_gcs_service):
        """Test successful file download."""
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_gcs_service._mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_blob.exists.return_value = True
        mock_blob.download_as_bytes.return_value = b"downloaded content"

        result = await mock_gcs_service.download_file(
            bucket_name="test-bucket",
            file_path="test-env/downloads/test.txt",  # Path should already be prefixed
        )

        mock_bucket.blob.assert_called_once_with("test-env/downloads/test.txt")
        mock_blob.download_as_bytes.assert_called_once()
        assert result == b"downloaded content"

    @pytest.mark.asyncio
    async def test_download_file_not_found(self, mock_gcs_service):
        """Test downloading non-existent file."""
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_gcs_service._mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_blob.exists.return_value = False

        with pytest.raises(StorageNotFoundError, match="File not found"):
            await mock_gcs_service.download_file(
                bucket_name="test-bucket", file_path="missing.txt"
            )

    @pytest.mark.asyncio
    async def test_delete_file_success(self, mock_gcs_service):
        """Test successful file deletion."""
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_gcs_service._mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_blob.exists.return_value = True

        result = await mock_gcs_service.delete_file(
            bucket_name="test-bucket", file_path="test-env/deleteme.txt"
        )

        mock_blob.delete.assert_called_once()
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, mock_gcs_service):
        """Test deleting non-existent file."""
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_gcs_service._mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_blob.exists.return_value = False

        result = await mock_gcs_service.delete_file(
            bucket_name="test-bucket", file_path="missing.txt"
        )

        mock_blob.delete.assert_not_called()
        assert result is False

    @pytest.mark.asyncio
    async def test_file_exists(self, mock_gcs_service):
        """Test checking if file exists."""
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_gcs_service._mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_blob.exists.return_value = True

        result = await mock_gcs_service.file_exists(
            bucket_name="test-bucket", file_path="test-env/check.txt"
        )

        mock_bucket.blob.assert_called_once_with("test-env/check.txt")
        mock_blob.exists.assert_called_once()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_file_info(self, mock_gcs_service):
        """Test retrieving file metadata."""
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_gcs_service._mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_blob.exists.return_value = True
        mock_blob.size = 2048
        mock_blob.content_type = "image/png"
        mock_blob.metadata = {"author": "test"}
        mock_blob.time_created = datetime.now()
        mock_blob.updated = datetime.now()
        mock_blob.etag = "test-etag"

        result = await mock_gcs_service.get_file_info(
            bucket_name="test-bucket", file_path="test-env/meta.png"
        )

        mock_blob.reload.assert_called_once()
        assert result["size"] == 2048
        assert result["content_type"] == "image/png"
        assert result["metadata"]["author"] == "test"
        assert result["etag"] == "test-etag"

    @pytest.mark.asyncio
    async def test_get_file_info_not_found(self, mock_gcs_service):
        """Test getting info for non-existent file."""
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_gcs_service._mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_blob.exists.return_value = False

        with pytest.raises(StorageNotFoundError, match="File not found"):
            await mock_gcs_service.get_file_info(
                bucket_name="test-bucket", file_path="missing.txt"
            )

    @pytest.mark.asyncio
    async def test_generate_signed_url_get(self, mock_gcs_service):
        """Test generating signed URL for download."""
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_gcs_service._mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_blob.generate_signed_url.return_value = "https://signed-download-url"

        result = await mock_gcs_service.generate_signed_url(
            bucket_name="test-bucket",
            file_path="test-env/downloads/doc.pdf",  # Already prefixed for GET
            method="GET",
        )

        # For GET, path should not be prefixed again
        mock_bucket.blob.assert_called_once_with("test-env/downloads/doc.pdf")

        mock_blob.generate_signed_url.assert_called_once()
        call_kwargs = mock_blob.generate_signed_url.call_args[1]
        assert call_kwargs["method"] == "GET"
        assert call_kwargs["version"] == "v4"

        assert result == "https://signed-download-url"

    @pytest.mark.asyncio
    async def test_list_files(self, mock_gcs_service):
        """Test listing files in a bucket."""
        mock_bucket = Mock()
        mock_gcs_service._mock_client.bucket.return_value = mock_bucket

        # Create mock blobs
        mock_blobs = []
        for i in range(3):
            blob = Mock()
            blob.name = f"test-env/file{i}.txt"
            mock_blobs.append(blob)

        mock_bucket.list_blobs.return_value = mock_blobs

        result = await mock_gcs_service.list_files(
            bucket_name="test-bucket", prefix="test-env/", limit=10
        )

        mock_bucket.list_blobs.assert_called_once_with(
            prefix="test-env/", max_results=10
        )

        assert len(result) == 3
        assert all(name.startswith("test-env/") for name in result)

    @pytest.mark.asyncio
    async def test_create_bucket_success(self, mock_gcs_service):
        """Test creating a new bucket."""
        mock_bucket = Mock()
        mock_gcs_service._mock_client.bucket.return_value = mock_bucket

        mock_bucket.exists.return_value = False

        result = await mock_gcs_service.create_bucket(
            bucket_name="new-bucket", location="us-central1"
        )

        mock_bucket.create.assert_called_once_with(location="us-central1")
        assert result is True

    @pytest.mark.asyncio
    async def test_create_bucket_already_exists(self, mock_gcs_service):
        """Test creating a bucket that already exists."""
        mock_bucket = Mock()
        mock_gcs_service._mock_client.bucket.return_value = mock_bucket

        mock_bucket.exists.return_value = True

        result = await mock_gcs_service.create_bucket("existing-bucket")

        mock_bucket.create.assert_not_called()
        assert result is False

    @pytest.mark.asyncio
    async def test_bucket_exists(self, mock_gcs_service):
        """Test checking if bucket exists."""
        mock_bucket = Mock()
        mock_gcs_service._mock_client.bucket.return_value = mock_bucket

        mock_bucket.exists.return_value = True

        result = await mock_gcs_service.bucket_exists("test-bucket")

        mock_bucket.exists.assert_called_once()
        assert result is True


class TestStorageServiceErrorHandling:
    """Test error handling in storage operations."""

    @pytest.mark.asyncio
    async def test_upload_permission_error(self, mock_gcs_service):
        """Test handling permission errors during upload."""
        from google.cloud.exceptions import Forbidden

        mock_bucket = Mock()
        mock_blob = Mock()
        mock_gcs_service._mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_blob.upload_from_string.side_effect = Forbidden("Permission denied")

        with pytest.raises(StoragePermissionError, match="Permission denied"):
            await mock_gcs_service.upload_file(
                bucket_name="test-bucket", file_path="error.txt", data=b"content"
            )

    @pytest.mark.asyncio
    async def test_download_permission_error(self, mock_gcs_service):
        """Test handling permission errors during download."""
        from google.cloud.exceptions import Forbidden

        mock_bucket = Mock()
        mock_blob = Mock()
        mock_gcs_service._mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_blob.exists.return_value = True
        mock_blob.download_as_bytes.side_effect = Forbidden("Permission denied")

        with pytest.raises(StoragePermissionError, match="Permission denied"):
            await mock_gcs_service.download_file(
                bucket_name="test-bucket", file_path="protected.txt"
            )

    @pytest.mark.asyncio
    async def test_delete_permission_error(self, mock_gcs_service):
        """Test handling permission errors during deletion."""
        from google.cloud.exceptions import Forbidden

        mock_bucket = Mock()
        mock_blob = Mock()
        mock_gcs_service._mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_blob.exists.return_value = True
        mock_blob.delete.side_effect = Forbidden("Permission denied")

        with pytest.raises(StoragePermissionError, match="Permission denied"):
            await mock_gcs_service.delete_file(
                bucket_name="test-bucket", file_path="protected.txt"
            )

    @pytest.mark.asyncio
    async def test_generic_storage_error(self, mock_gcs_service):
        """Test handling generic storage errors."""
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_gcs_service._mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_blob.upload_from_string.side_effect = Exception("Network error")

        with pytest.raises(StorageError, match="Upload failed"):
            await mock_gcs_service.upload_file(
                bucket_name="test-bucket", file_path="error.txt", data=b"content"
            )
