"""Buckets API router for Temasek POC Backend.

Provides bucket management endpoints with CRUD operations.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from core.dependencies import (
    AuthTokenDep,
    BucketServiceDep,
    DatabaseDep,
    FileServiceDep,
)
from core.logging import get_logger
from schemas.buckets import (
    BucketCreateRequest,
    BucketListResponse,
    BucketResponse,
    BucketUpdateRequest,
)
from schemas.files import FileListResponse, FileResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/buckets", tags=["buckets"])


@router.get("/", response_model=BucketListResponse)
async def list_buckets(
    token: AuthTokenDep,
    bucket_service: BucketServiceDep,
    db: DatabaseDep,
    limit: int = Query(default=100, description="Maximum number of buckets to return"),
):
    """List all buckets (regardless of creator).

    Returns all buckets in the system with pagination support.
    """
    try:
        buckets = await bucket_service.list_all_buckets(db, limit=limit)

        return BucketListResponse(
            buckets=[BucketResponse.from_bucket_model(bucket) for bucket in buckets],
            total=len(buckets),
        )

    except Exception as e:
        logger.error(f"Error listing buckets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list buckets",
        )


@router.post("/", response_model=BucketResponse, status_code=status.HTTP_201_CREATED)
async def create_bucket(
    bucket_data: BucketCreateRequest,
    token: AuthTokenDep,
    bucket_service: BucketServiceDep,
    db: DatabaseDep,
):
    """Create a new bucket.

    Creates a new storage bucket with the specified configuration.
    """
    try:
        # Get user from token
        user = token.get("user")
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found in token",
            )

        bucket = await bucket_service.create_bucket(
            name=bucket_data.name,
            slug=bucket_data.slug,
            created_by_user_id=user.id,
            db=db,
            provider=bucket_data.provider,
            is_public=bucket_data.is_public,
        )

        return BucketResponse.from_bucket_model(bucket)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating bucket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create bucket",
        )


@router.get("/{bucket_id}", response_model=BucketResponse)
async def get_bucket(
    bucket_id: UUID,
    token: AuthTokenDep,
    bucket_service: BucketServiceDep,
    db: DatabaseDep,
):
    """Get bucket by UUID."""
    try:
        bucket = await bucket_service.get_bucket_by_id(bucket_id, db)
        if not bucket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket with ID {bucket_id} not found",
            )

        return BucketResponse.from_bucket_model(bucket)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving bucket {bucket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bucket",
        )


@router.put("/{bucket_id}", response_model=BucketResponse)
async def update_bucket(
    bucket_id: UUID,
    update_data: BucketUpdateRequest,
    token: AuthTokenDep,
    bucket_service: BucketServiceDep,
    db: DatabaseDep,
):
    """Update bucket properties."""
    try:
        # Get user from token
        user = token.get("user")
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found in token",
            )

        bucket = await bucket_service.update_bucket(
            bucket_id=bucket_id,
            updated_by_user_id=user.id,
            db=db,
            name=update_data.name,
            is_public=update_data.is_public,
        )

        if not bucket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket with ID {bucket_id} not found",
            )

        return BucketResponse.from_bucket_model(bucket)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating bucket {bucket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update bucket",
        )


@router.delete("/{bucket_id}", status_code=status.HTTP_200_OK)
async def delete_bucket(
    bucket_id: UUID,
    token: AuthTokenDep,
    bucket_service: BucketServiceDep,
    db: DatabaseDep,
):
    """Delete bucket."""
    try:
        # Get user from token
        user = token.get("user")
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found in token",
            )

        deleted = await bucket_service.delete_bucket(bucket_id, user.id, db)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket with ID {bucket_id} not found",
            )

        return {"message": "Bucket deleted successfully"}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting bucket {bucket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete bucket",
        )


@router.get("/{bucket_id}/files", response_model=FileListResponse)
async def list_bucket_files(
    bucket_id: UUID,
    token: AuthTokenDep,
    file_service: FileServiceDep,
    db: DatabaseDep,
    limit: int = Query(default=100, description="Maximum number of files to return"),
    offset: int = Query(default=0, description="Number of files to skip"),
):
    """List files in bucket (by UUID)."""
    try:
        files = await file_service.get_files_by_bucket(
            bucket_id, db, limit=limit, offset=offset
        )

        return FileListResponse(
            files=[FileResponse.from_file_model(file) for file in files],
            total=len(files),
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(f"Error listing files in bucket {bucket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list bucket files",
        )


@router.get("/by-slug/{slug}", response_model=BucketResponse)
async def get_bucket_by_slug(
    slug: str, token: AuthTokenDep, bucket_service: BucketServiceDep, db: DatabaseDep
):
    """Get bucket by slug."""
    try:
        bucket = await bucket_service.get_bucket_by_slug(slug, db)
        if not bucket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket with slug '{slug}' not found",
            )

        return BucketResponse.from_bucket_model(bucket)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving bucket by slug {slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bucket",
        )


@router.get("/by-slug/{slug}/files", response_model=FileListResponse)
async def list_bucket_files_by_slug(
    slug: str,
    token: AuthTokenDep,
    bucket_service: BucketServiceDep,
    file_service: FileServiceDep,
    db: DatabaseDep,
    limit: int = Query(default=100, description="Maximum number of files to return"),
    offset: int = Query(default=0, description="Number of files to skip"),
):
    """List files in bucket (by slug)."""
    try:
        # First get the bucket by slug
        bucket = await bucket_service.get_bucket_by_slug(slug, db)
        if not bucket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket with slug '{slug}' not found",
            )

        # Then get files in that bucket
        files = await file_service.get_files_by_bucket(
            bucket.id, db, limit=limit, offset=offset
        )

        return FileListResponse(
            files=[FileResponse.from_file_model(file) for file in files],
            total=len(files),
            limit=limit,
            offset=offset,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing files in bucket {slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list bucket files",
        )


# Export for easy imports
__all__ = ["router"]
