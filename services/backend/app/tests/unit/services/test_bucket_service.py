"""Unit tests for BucketService with mocked dependencies."""

from uuid import uuid4

import pytest

from services.bucket_service import BucketService


class TestBucketServiceCreate:
    """Test bucket creation functionality."""

    @pytest.mark.asyncio
    async def test_creates_new_bucket(self, mocker):
        """Test successful bucket creation."""
        service = BucketService()
        mock_db = mocker.AsyncMock()
        mock_db.add = mocker.Mock()
        mock_db.commit = mocker.AsyncMock()
        mock_db.refresh = mocker.AsyncMock()

        user_id = uuid4()

        # Mock user check
        mock_user = mocker.Mock()
        mock_user_result = mocker.Mock()
        mock_user_result.scalar_one_or_none.return_value = mock_user

        # Mock bucket check (no existing bucket)
        mock_bucket_result = mocker.Mock()
        mock_bucket_result.scalar_one_or_none.return_value = None

        # Set up execute to return different results
        mock_db.execute.side_effect = [mock_bucket_result, mock_user_result]

        await service.create_bucket(
            name="test-bucket",
            slug="test-bucket",
            created_by_user_id=user_id,
            db=mock_db,
            provider="gcp",
            is_public=False,
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

        # Check the bucket that was added
        added_bucket = mock_db.add.call_args[0][0]
        assert added_bucket.name == "test-bucket"
        assert added_bucket.slug == "test-bucket"
        assert added_bucket.provider == "gcp"
        assert added_bucket.is_public is False
        assert added_bucket.created_by_id == user_id
        assert added_bucket.updated_by_id == user_id

    @pytest.mark.asyncio
    async def test_create_bucket_handles_duplicate_slug(self, mocker):
        """Test that duplicate slug raises appropriate error."""
        service = BucketService()
        mock_db = mocker.AsyncMock()

        # Mock that bucket already exists
        mock_existing_bucket = mocker.Mock()

        # Mock the _get_bucket_by_slug_query method to return existing bucket
        mocker.patch.object(
            service, "_get_bucket_by_slug_query", return_value=mock_existing_bucket
        )
        with pytest.raises(ValueError, match="Bucket with slug .* already exists"):
            await service.create_bucket(
                name="test-bucket",
                slug="duplicate-slug",
                created_by_user_id=uuid4(),
                db=mock_db,
            )

    @pytest.mark.asyncio
    async def test_create_bucket_validates_empty_name(self, mocker):
        """Test that empty bucket name raises ValueError."""
        service = BucketService()
        mock_db = mocker.AsyncMock()

        with pytest.raises(ValueError, match="Bucket name cannot be empty"):
            await service.create_bucket(
                name="", slug="test-slug", created_by_user_id=uuid4(), db=mock_db
            )

    @pytest.mark.asyncio
    async def test_create_bucket_validates_empty_slug(self, mocker):
        """Test that empty bucket slug raises ValueError."""
        service = BucketService()
        mock_db = mocker.AsyncMock()

        with pytest.raises(ValueError, match="Bucket slug cannot be empty"):
            await service.create_bucket(
                name="test-bucket", slug="", created_by_user_id=uuid4(), db=mock_db
            )


class TestBucketServiceGetters:
    """Test bucket retrieval methods."""

    @pytest.mark.asyncio
    async def test_get_bucket_by_id(self, mocker):
        """Test successful bucket retrieval by ID."""
        service = BucketService()
        mock_db = mocker.AsyncMock()
        bucket_id = uuid4()

        mock_bucket = mocker.Mock()
        mock_bucket.id = bucket_id
        mock_bucket.name = "test-bucket"

        mock_result = mocker.Mock()
        mock_result.scalar_one_or_none.return_value = mock_bucket
        mock_db.execute.return_value = mock_result

        result = await service.get_bucket_by_id(bucket_id, mock_db)
        assert result == mock_bucket

    @pytest.mark.asyncio
    async def test_get_bucket_by_id_not_found(self, mocker):
        """Test get_bucket_by_id returns None when not found."""
        service = BucketService()
        mock_db = mocker.AsyncMock()

        mock_result = mocker.Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_bucket_by_id(uuid4(), mock_db)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_bucket_by_slug(self, mocker):
        """Test successful bucket retrieval by slug."""
        service = BucketService()
        mock_db = mocker.AsyncMock()

        mock_bucket = mocker.Mock()
        mock_bucket.slug = "test-slug"
        mock_bucket.name = "test-bucket"

        mock_result = mocker.Mock()
        mock_result.scalar_one_or_none.return_value = mock_bucket
        mock_db.execute.return_value = mock_result

        result = await service.get_bucket_by_slug("test-slug", mock_db)
        assert result == mock_bucket

    @pytest.mark.asyncio
    async def test_get_bucket_by_slug_not_found(self, mocker):
        """Test get_bucket_by_slug returns None when not found."""
        service = BucketService()
        mock_db = mocker.AsyncMock()

        mock_result = mocker.Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_bucket_by_slug("non-existent", mock_db)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_all_buckets(self, mocker):
        """Test listing all buckets."""
        service = BucketService()
        mock_db = mocker.AsyncMock()

        mock_bucket1 = mocker.Mock()
        mock_bucket1.name = "bucket1"
        mock_bucket2 = mocker.Mock()
        mock_bucket2.name = "bucket2"

        mock_result = mocker.Mock()
        mock_result.scalars.return_value.all.return_value = [mock_bucket1, mock_bucket2]
        mock_db.execute.return_value = mock_result

        result = await service.list_all_buckets(mock_db, limit=10)
        assert len(result) == 2
        assert result[0] == mock_bucket1
        assert result[1] == mock_bucket2


class TestBucketServiceUpdate:
    """Test bucket update functionality."""

    @pytest.mark.asyncio
    async def test_update_bucket_name(self, mocker):
        """Test updating bucket name."""
        service = BucketService()
        mock_db = mocker.AsyncMock()
        bucket_id = uuid4()
        user_id = uuid4()

        mock_bucket = mocker.Mock()
        mock_bucket.id = bucket_id
        mock_bucket.name = "old-name"
        mock_bucket.slug = "test-slug"

        mocker.patch.object(service, "get_bucket_by_id", return_value=mock_bucket)
        await service.update_bucket(
            bucket_id=bucket_id, updated_by_user_id=user_id, db=mock_db, name="new-name"
        )

        assert mock_bucket.name == "new-name"
        assert mock_bucket.updated_by_id == user_id
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_bucket_is_public(self, mocker):
        """Test updating bucket public status."""
        service = BucketService()
        mock_db = mocker.AsyncMock()
        bucket_id = uuid4()
        user_id = uuid4()

        mock_bucket = mocker.Mock()
        mock_bucket.id = bucket_id
        mock_bucket.is_public = False

        mocker.patch.object(service, "get_bucket_by_id", return_value=mock_bucket)
        await service.update_bucket(
            bucket_id=bucket_id, updated_by_user_id=user_id, db=mock_db, is_public=True
        )

        assert mock_bucket.is_public is True

    @pytest.mark.asyncio
    async def test_update_nonexistent_bucket(self, mocker):
        """Test updating non-existent bucket returns None."""
        service = BucketService()
        mock_db = mocker.AsyncMock()

        mocker.patch.object(service, "get_bucket_by_id", return_value=None)
        result = await service.update_bucket(
            bucket_id=uuid4(), updated_by_user_id=uuid4(), db=mock_db, name="new-name"
        )

        assert result is None
        mock_db.commit.assert_not_called()


class TestBucketServiceDelete:
    """Test bucket deletion functionality."""

    @pytest.mark.asyncio
    async def test_delete_empty_bucket(self, mocker):
        """Test successful deletion of empty bucket."""
        service = BucketService()
        mock_db = mocker.AsyncMock()
        bucket_id = uuid4()
        user_id = uuid4()

        mock_bucket = mocker.Mock()
        mock_bucket.id = bucket_id
        mock_bucket.created_by_id = user_id  # User is the creator

        mocker.patch.object(service, "get_bucket_by_id", return_value=mock_bucket)
        result = await service.delete_bucket(bucket_id, user_id, mock_db)

        assert result is True
        mock_db.delete.assert_called_once_with(mock_bucket)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cannot_delete_bucket_without_permission(self, mocker):
        """Test that bucket cannot be deleted by non-owner."""
        service = BucketService()
        mock_db = mocker.AsyncMock()
        bucket_id = uuid4()
        owner_id = uuid4()
        other_user_id = uuid4()

        mock_bucket = mocker.Mock()
        mock_bucket.id = bucket_id
        mock_bucket.created_by_id = owner_id  # Different user is the creator

        mocker.patch.object(service, "get_bucket_by_id", return_value=mock_bucket)
        with pytest.raises(
            ValueError, match="User does not have permission to delete this bucket"
        ):
            await service.delete_bucket(bucket_id, other_user_id, mock_db)

        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_bucket(self, mocker):
        """Test deleting non-existent bucket returns False."""
        service = BucketService()
        mock_db = mocker.AsyncMock()
        user_id = uuid4()

        mocker.patch.object(service, "get_bucket_by_id", return_value=None)
        result = await service.delete_bucket(uuid4(), user_id, mock_db)

        assert result is False
        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()
