"""Unit tests for FileService with mocked dependencies."""

from uuid import uuid4

import pytest

from services.file_service import FileService


class TestFileServiceCreate:
    """Test file creation functionality."""

    @pytest.mark.asyncio
    async def test_create_file_record(self, mocker):
        """Test successful file record creation."""
        service = FileService()
        mock_db = mocker.AsyncMock()
        mock_db.add = mocker.Mock()
        mock_db.commit = mocker.AsyncMock()
        mock_db.refresh = mocker.AsyncMock()

        bucket_id = uuid4()
        user_id = uuid4()

        # Mock bucket exists check
        mock_bucket = mocker.Mock()
        mock_bucket.id = bucket_id
        mock_bucket_result = mocker.Mock()
        mock_bucket_result.scalar_one_or_none.return_value = mock_bucket
        mock_db.execute.return_value = mock_bucket_result

        await service.create_file_record(
            filename="test-file.pdf",
            original_filename="test-file.pdf",
            bucket_id=bucket_id,
            file_size=1024,
            content_type="application/pdf",
            storage_path="bucket/test-file.pdf",
            created_by_id=user_id,
            db=mock_db,
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

        # Check the file that was added
        added_file = mock_db.add.call_args[0][0]
        assert added_file.bucket_id == bucket_id
        assert added_file.filename == "test-file.pdf"
        assert added_file.original_filename == "test-file.pdf"
        assert added_file.extension == ".pdf"
        assert added_file.file_size == 1024
        assert added_file.content_type == "application/pdf"
        assert added_file.storage_path == "bucket/test-file.pdf"
        assert added_file.created_by_id == user_id

    @pytest.mark.asyncio
    async def test_create_file_bucket_not_found(self, mocker):
        """Test that creating file with non-existent bucket raises ValueError."""
        service = FileService()
        mock_db = mocker.AsyncMock()

        # Mock bucket doesn't exist
        mock_bucket_result = mocker.Mock()
        mock_bucket_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_bucket_result

        with pytest.raises(ValueError, match="Bucket with ID .* not found"):
            await service.create_file_record(
                filename="test.pdf",
                original_filename="test.pdf",
                bucket_id=uuid4(),
                file_size=1024,
                content_type="application/pdf",
                storage_path="path/to/file",
                created_by_id=uuid4(),
                db=mock_db,
            )


class TestFileServiceGetters:
    """Test file retrieval methods."""

    @pytest.mark.asyncio
    async def test_get_file_by_id(self, mocker):
        """Test successful file retrieval by ID."""
        service = FileService()
        mock_db = mocker.AsyncMock()
        file_id = uuid4()

        mock_file = mocker.Mock()
        mock_file.id = file_id
        mock_file.filename = "test.pdf"

        mock_result = mocker.Mock()
        mock_result.scalar_one_or_none.return_value = mock_file
        mock_db.execute.return_value = mock_result

        result = await service.get_file_by_id(file_id, mock_db)
        assert result == mock_file

    @pytest.mark.asyncio
    async def test_get_file_by_id_not_found(self, mocker):
        """Test get_file_by_id returns None when not found."""
        service = FileService()
        mock_db = mocker.AsyncMock()

        mock_result = mocker.Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_file_by_id(uuid4(), mock_db)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_file_by_id_or_404_found(self, mocker):
        """Test get_file_by_id_or_404 returns file when found."""
        service = FileService()
        mock_db = mocker.AsyncMock()
        file_id = uuid4()

        mock_file = mocker.Mock()
        mock_file.id = file_id

        mocker.patch.object(service, "get_file_by_id", return_value=mock_file)
        result = await service.get_file_by_id_or_404(file_id, mock_db)
        assert result == mock_file

    @pytest.mark.asyncio
    async def test_get_file_by_id_or_404_not_found(self, mocker):
        """Test get_file_by_id_or_404 raises 404 when not found."""
        service = FileService()
        mock_db = mocker.AsyncMock()

        mocker.patch.object(service, "get_file_by_id", return_value=None)
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await service.get_file_by_id_or_404(uuid4(), mock_db)

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_files_by_bucket(self, mocker):
        """Test retrieving files by bucket ID."""
        service = FileService()
        mock_db = mocker.AsyncMock()
        bucket_id = uuid4()

        mock_file1 = mocker.Mock()
        mock_file1.filename = "file1.pdf"
        mock_file2 = mocker.Mock()
        mock_file2.filename = "file2.pdf"

        mock_result = mocker.Mock()
        mock_result.scalars.return_value.all.return_value = [mock_file1, mock_file2]
        mock_db.execute.return_value = mock_result

        result = await service.get_files_by_bucket(bucket_id, mock_db, limit=10)
        assert len(result) == 2
        assert result[0] == mock_file1
        assert result[1] == mock_file2

    @pytest.mark.asyncio
    async def test_get_files_by_user(self, mocker):
        """Test retrieving files by user ID."""
        service = FileService()
        mock_db = mocker.AsyncMock()
        user_id = uuid4()

        mock_file1 = mocker.Mock()
        mock_file1.filename = "file1.pdf"
        mock_file2 = mocker.Mock()
        mock_file2.filename = "file2.pdf"

        mock_result = mocker.Mock()
        mock_result.scalars.return_value.all.return_value = [mock_file1, mock_file2]
        mock_db.execute.return_value = mock_result

        result = await service.get_files_by_user(user_id, mock_db, limit=10)
        assert len(result) == 2
        assert result[0] == mock_file1
        assert result[1] == mock_file2


class TestFileServiceSearch:
    """Test file search functionality."""

    @pytest.mark.asyncio
    async def test_search_files_by_query(self, mocker):
        """Test searching files by query text."""
        service = FileService()
        mock_db = mocker.AsyncMock()

        mock_file = mocker.Mock()
        mock_file.filename = "report.pdf"

        mock_result = mocker.Mock()
        mock_result.scalars.return_value.all.return_value = [mock_file]
        mock_db.execute.return_value = mock_result

        result = await service.search_files(
            query_text="report", db=mock_db, limit=10, offset=0
        )

        assert len(result) == 1
        assert result[0] == mock_file

    @pytest.mark.asyncio
    async def test_search_files_empty_query(self, mocker):
        """Test searching files with empty query returns all files."""
        service = FileService()
        mock_db = mocker.AsyncMock()

        mock_file1 = mocker.Mock()
        mock_file2 = mocker.Mock()

        mock_result = mocker.Mock()
        mock_result.scalars.return_value.all.return_value = [mock_file1, mock_file2]
        mock_db.execute.return_value = mock_result

        result = await service.search_files(
            query_text="", db=mock_db, limit=10, offset=0
        )

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_search_files_with_bucket_filter(self, mocker):
        """Test searching files with bucket filter."""
        service = FileService()
        mock_db = mocker.AsyncMock()
        bucket_id = uuid4()

        mock_file = mocker.Mock()
        mock_file.filename = "report.pdf"
        mock_file.bucket_id = bucket_id

        mock_result = mocker.Mock()
        mock_result.scalars.return_value.all.return_value = [mock_file]
        mock_db.execute.return_value = mock_result

        result = await service.search_files(
            query_text="report", db=mock_db, bucket_id=bucket_id, limit=10, offset=0
        )

        assert len(result) == 1
        assert result[0].bucket_id == bucket_id

    @pytest.mark.asyncio
    async def test_search_files_with_content_type_filter(self, mocker):
        """Test searching files with content type filter."""
        service = FileService()
        mock_db = mocker.AsyncMock()

        mock_file = mocker.Mock()
        mock_file.filename = "report.pdf"
        mock_file.content_type = "application/pdf"

        mock_result = mocker.Mock()
        mock_result.scalars.return_value.all.return_value = [mock_file]
        mock_db.execute.return_value = mock_result

        result = await service.search_files(
            query_text="report",
            db=mock_db,
            content_type="application/pdf",
            limit=10,
            offset=0,
        )

        assert len(result) == 1
        assert result[0].content_type == "application/pdf"


class TestFileServiceUpdate:
    """Test file update functionality."""

    @pytest.mark.asyncio
    async def test_update_file_metadata(self, mocker):
        """Test updating file metadata."""
        service = FileService()
        mock_db = mocker.AsyncMock()
        file_id = uuid4()
        user_id = uuid4()

        mock_file = mocker.Mock()
        mock_file.id = file_id
        mock_file.filename = "old-name.pdf"

        mock_result = mocker.Mock()
        mock_result.scalar_one_or_none.return_value = mock_file
        mock_db.execute.return_value = mock_result

        new_metadata = {"department": "finance", "year": 2024}

        await service.update_file_metadata(
            file_id=file_id,
            filename="new-name.pdf",
            metadata=new_metadata,
            updated_by_id=user_id,
            db=mock_db,
        )

        assert mock_file.filename == "new-name.pdf"
        assert mock_file.updated_by_id == user_id
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_file_metadata_not_found(self, mocker):
        """Test updating non-existent file returns None."""
        service = FileService()
        mock_db = mocker.AsyncMock()

        mock_result = mocker.Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.update_file_metadata(
            file_id=uuid4(),
            filename="new-name.pdf",
            metadata={},
            updated_by_id=uuid4(),
            db=mock_db,
        )

        assert result is None
        mock_db.commit.assert_not_called()


class TestFileServiceDelete:
    """Test file deletion functionality."""

    @pytest.mark.asyncio
    async def test_delete_file_record(self, mocker):
        """Test successful file deletion."""
        service = FileService()
        mock_db = mocker.AsyncMock()
        file_id = uuid4()

        mock_file = mocker.Mock()
        mock_file.id = file_id

        mock_result = mocker.Mock()
        mock_result.scalar_one_or_none.return_value = mock_file
        mock_db.execute.return_value = mock_result

        result = await service.delete_file_record(file_id, mock_db)

        assert result is True
        mock_db.delete.assert_called_once_with(mock_file)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, mocker):
        """Test deleting non-existent file returns False."""
        service = FileService()
        mock_db = mocker.AsyncMock()

        mock_result = mocker.Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.delete_file_record(uuid4(), mock_db)

        assert result is False
        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()


class TestFileServiceStats:
    """Test file statistics functionality."""

    @pytest.mark.asyncio
    async def test_get_file_stats(self, mocker):
        """Test getting file statistics."""
        service = FileService()
        mock_db = mocker.AsyncMock()

        # Mock stats result
        mock_stats = mocker.Mock()
        mock_stats.total_files = 10
        mock_stats.total_size = 1048576  # 1MB
        mock_stats.avg_size = 104857.6

        mock_result = mocker.Mock()
        mock_result.first.return_value = mock_stats
        mock_db.execute.return_value = mock_result

        result = await service.get_file_stats(mock_db)

        assert result["total_files"] == 10
        assert result["total_size_bytes"] == 1048576
        assert result["average_size_bytes"] == 104857.6

    @pytest.mark.asyncio
    async def test_get_file_stats_with_bucket_filter(self, mocker):
        """Test getting file statistics for specific bucket."""
        service = FileService()
        mock_db = mocker.AsyncMock()
        bucket_id = uuid4()

        # Mock stats result
        mock_stats = mocker.Mock()
        mock_stats.total_files = 5
        mock_stats.total_size = 524288
        mock_stats.avg_size = 104857.6

        mock_result = mocker.Mock()
        mock_result.first.return_value = mock_stats
        mock_db.execute.return_value = mock_result

        result = await service.get_file_stats(mock_db, bucket_id=bucket_id)

        assert result["total_files"] == 5
        assert result["total_size_bytes"] == 524288
        assert result["average_size_bytes"] == 104857.6


class TestFileServiceHelpers:
    """Test helper methods."""

    @pytest.mark.asyncio
    async def test_file_exists_in_db_true(self, mocker):
        """Test file_exists_in_db returns True when file exists."""
        service = FileService()
        mock_db = mocker.AsyncMock()
        file_id = uuid4()

        mock_result = mocker.Mock()
        mock_result.scalar.return_value = 1  # Count of 1 means file exists
        mock_db.execute.return_value = mock_result

        result = await service.file_exists_in_db(file_id, mock_db)
        assert result is True

    @pytest.mark.asyncio
    async def test_file_exists_in_db_false(self, mocker):
        """Test file_exists_in_db returns False when file doesn't exist."""
        service = FileService()
        mock_db = mocker.AsyncMock()

        mock_result = mocker.Mock()
        mock_result.scalar.return_value = 0  # Count of 0 means file doesn't exist
        mock_db.execute.return_value = mock_result

        result = await service.file_exists_in_db(uuid4(), mock_db)
        assert result is False
