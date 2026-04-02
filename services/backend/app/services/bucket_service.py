"""Bucket service for Temasek POC Backend.

Handles bucket metadata management with user ownership and cloud storage integration.
Provides CRUD operations for storage buckets with proper user access control.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from packages.db.models import Bucket, User

from .storage import StorageProvider

logger = get_logger(__name__)


class BucketService:
    """Service for managing storage buckets."""

    async def create_bucket(
        self,
        name: str,
        slug: str,
        created_by_user_id: UUID,
        db: AsyncSession,
        provider: str = StorageProvider.DEFAULT,
        is_public: bool = False,
    ) -> Bucket:
        """Create a new storage bucket.

        Args:
            name: Actual bucket name (e.g., 'investment-reports-dev')
            slug: Human-readable slug for URLs (e.g., 'investment-reports')
            created_by_user_id: User ID who is creating the bucket
            db: Database session to use for the operation
            provider: Cloud provider ('gcp', 'aws', 'azure')
            is_public: Whether bucket contents are publicly accessible

        Returns:
            Created bucket model instance

        Raises:
            ValueError: If validation fails or slug already exists
        """
        # Validate inputs
        if not name or not name.strip():
            raise ValueError("Bucket name cannot be empty")
        if not slug or not slug.strip():
            raise ValueError("Bucket slug cannot be empty")

        name = name.strip()
        slug = slug.strip().lower()

        # Validate slug format (basic validation)
        if not slug.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Slug can only contain letters, numbers, hyphens, and underscores"
            )

        # Validate provider
        if provider not in StorageProvider.ALL:
            raise ValueError(
                f"Invalid provider: {provider}. Must be one of {StorageProvider.ALL}"
            )

        try:
            # Check if slug already exists
            existing_bucket = await self._get_bucket_by_slug_query(slug, db)
            if existing_bucket:
                raise ValueError(f"Bucket with slug '{slug}' already exists")

            # Verify the user exists
            user_check = await db.execute(
                select(User).where(User.id == created_by_user_id)
            )
            if not user_check.scalar_one_or_none():
                raise ValueError(f"User with ID {created_by_user_id} does not exist")

            # Create new bucket
            new_bucket = Bucket(
                name=name,
                slug=slug,
                provider=provider,
                is_public=is_public,
                created_by_id=created_by_user_id,
                updated_by_id=created_by_user_id,
            )

            db.add(new_bucket)
            await db.commit()
            await db.refresh(new_bucket)

            logger.info(
                f"Created bucket '{name}' (slug: {slug}) for user {created_by_user_id}"
            )
            return new_bucket

        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Failed to create bucket '{name}' (slug: {slug}): {e}")
            raise ValueError(
                f"Failed to create bucket: bucket with slug '{slug}' may already exist"
            ) from e

    async def get_bucket_by_slug(self, slug: str, db: AsyncSession) -> Bucket | None:
        """Get bucket by slug.

        Args:
            slug: Human-readable slug for the bucket
            db: Database session to use for the operation

        Returns:
            Bucket model instance or None if not found
        """
        if not slug or not slug.strip():
            return None

        slug = slug.strip().lower()
        return await self._get_bucket_by_slug_query(slug, db)

    async def _get_bucket_by_slug_query(
        self, slug: str, db: AsyncSession
    ) -> Bucket | None:
        """Internal method to execute the query."""
        try:
            stmt = select(Bucket).where(Bucket.slug == slug)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error querying bucket by slug {slug}: {e}")
            return None

    async def get_bucket_by_id(
        self, bucket_id: UUID, db: AsyncSession
    ) -> Bucket | None:
        """Get bucket by internal database ID.

        Args:
            bucket_id: Internal database UUID for the bucket
            db: Database session to use for the operation

        Returns:
            Bucket model instance or None if not found
        """
        try:
            stmt = select(Bucket).where(Bucket.id == bucket_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error querying bucket by ID {bucket_id}: {e}")
            return None

    async def get_bucket_by_id_or_404(
        self, bucket_id: UUID, db: AsyncSession
    ) -> Bucket:
        """Get bucket by ID or raise 404 if not found.

        Args:
            bucket_id: Internal database UUID for the bucket
            db: Database session to use for the operation

        Returns:
            Bucket model instance

        Raises:
            HTTPException: 404 if bucket not found
        """
        from fastapi import HTTPException, status

        bucket = await self.get_bucket_by_id(bucket_id, db)
        if not bucket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket with ID {bucket_id} not found",
            )
        return bucket

    async def update_bucket(
        self,
        bucket_id: UUID,
        updated_by_user_id: UUID,
        db: AsyncSession,
        name: str | None = None,
        is_public: bool | None = None,
    ) -> Bucket | None:
        """Update bucket properties.

        Args:
            bucket_id: Internal database UUID for the bucket
            updated_by_user_id: User ID performing the update
            db: Database session to use for the operation
            name: New bucket name (optional)
            is_public: New public access setting (optional)

        Returns:
            Updated bucket model instance or None if not found

        Note:
            Slug cannot be updated to maintain URL stability
        """
        try:
            bucket = await self.get_bucket_by_id(bucket_id, db)
            if not bucket:
                return None

            # Update fields if provided
            if name is not None:
                bucket.name = name.strip()
            if is_public is not None:
                bucket.is_public = is_public

            bucket.updated_by_id = updated_by_user_id

            await db.commit()
            await db.refresh(bucket)

            logger.info(f"Updated bucket {bucket_id} by user {updated_by_user_id}")
            return bucket

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating bucket {bucket_id}: {e}")
            raise ValueError(f"Failed to update bucket: {str(e)}") from e

    async def delete_bucket(
        self, bucket_id: UUID, user_id: UUID, db: AsyncSession
    ) -> bool:
        """Delete bucket by ID.

        Args:
            bucket_id: Internal database UUID for the bucket
            user_id: User ID requesting deletion (for access control)
            db: Database session to use for the operation

        Returns:
            True if bucket was deleted, False if bucket didn't exist

        Raises:
            ValueError: If user doesn't have permission to delete bucket
        """
        try:
            bucket = await self.get_bucket_by_id(bucket_id, db)
            if not bucket:
                logger.debug(f"Bucket not found for deletion: {bucket_id}")
                return False

            # Check if user has permission to delete (must be creator)
            if bucket.created_by_id != user_id:
                raise ValueError("User does not have permission to delete this bucket")

            await db.delete(bucket)
            await db.commit()

            logger.info(f"Deleted bucket {bucket_id} by user {user_id}")
            return True

        except ValueError:
            raise  # Re-raise permission errors
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting bucket {bucket_id}: {e}")
            raise ValueError(f"Failed to delete bucket: {str(e)}") from e

    async def bucket_exists(self, slug: str, db: AsyncSession) -> bool:
        """Check if bucket exists by slug.

        Args:
            slug: Human-readable slug for the bucket
            db: Database session to use for the operation

        Returns:
            True if bucket exists, False otherwise
        """
        bucket = await self.get_bucket_by_slug(slug, db)
        return bucket is not None

    async def list_all_buckets(
        self, db: AsyncSession, limit: int | None = None
    ) -> list[Bucket]:
        """List all buckets (admin function).

        Args:
            db: Database session to use for the operation
            limit: Maximum number of buckets to return

        Returns:
            List of bucket model instances
        """
        try:
            stmt = select(Bucket).order_by(Bucket.created_at.desc())
            if limit:
                stmt = stmt.limit(limit)

            result = await db.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error listing all buckets: {e}")
            return []


def get_bucket_service() -> BucketService:
    """Create bucket service instance with dependency injection.

    FastAPI will cache this per request, so we don't create multiple instances
    within the same request context.

    Returns:
        BucketService instance
    """
    return BucketService()
