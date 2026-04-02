"""File service for managing file metadata in the database.

Handles CRUD operations for file records and metadata management.
Does not handle actual file storage - that's handled by StorageService.
"""

import os
from datetime import datetime, UTC
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.logging import get_logger
from packages.db.models import Bucket, File

logger = get_logger(__name__)


class FileService:
    """Service for managing file metadata in the database.

    This service handles:
    - Database CRUD operations for file records
    - File metadata management
    - File search and statistics
    - File validation (size, type, extension)

    Note: Does not handle actual file storage operations.
    Use StorageService for cloud storage operations.
    """

    # Validation constants
    MAX_FILE_SIZE_MB = 100  # Maximum file size in MB

    ALLOWED_MIME_TYPES = [
        # Images
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/bmp",
        # Documents
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        # Text
        "text/plain",
        "text/csv",
        "text/xml",
        # Archives
        "application/zip",
        "application/x-rar-compressed",
        "application/x-7z-compressed",
        # Data
        "application/json",
        # Code
        "text/javascript",
        "text/css",
        "text/html",
        "application/javascript",
    ]

    ALLOWED_EXTENSIONS = [
        # Documents
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        # Text
        ".txt",
        ".csv",
        ".json",
        ".xml",
        # Images
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".bmp",
        # Archives
        ".zip",
        ".rar",
        ".7z",
        # Code
        ".js",
        ".css",
        ".html",
        ".py",
        ".java",
        ".cpp",
        ".c",
    ]

    def validate_file_type(
        self, filename: str | None, content_type: str | None
    ) -> None:
        """Validate file type based on filename and content type.

        Args:
            filename: Name of the file to validate
            content_type: MIME type of the file

        Raises:
            HTTPException: If file type is not allowed
        """
        # Check content type
        if content_type and content_type not in self.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"File type '{content_type}' is not allowed",
            )

        # Check file extension
        if filename:
            _, ext = os.path.splitext(filename.lower())
            if ext and ext not in self.ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"File extension '{ext}' is not allowed",
                )

    def validate_file_size(self, file_size: int) -> None:
        """Validate file size against maximum allowed.

        Args:
            file_size: Size of the file in bytes

        Raises:
            HTTPException: If file size exceeds maximum
        """
        max_size_bytes = self.MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({file_size} bytes) exceeds maximum allowed ({max_size_bytes} bytes)",
            )

    async def create_file_record(
        self,
        filename: str,
        original_filename: str,
        bucket_id: UUID,
        file_size: int,
        content_type: str,
        storage_path: str,
        created_by_id: UUID,
        db: AsyncSession,
        metadata: dict | None = None,
    ) -> File:
        """Create a file metadata record in the database.

        Args:
            filename: Stored filename (may be different from original)
            original_filename: Original filename from upload
            bucket_id: ID of the bucket containing this file
            file_size: Size of file in bytes
            content_type: MIME type of the file
            storage_path: Path in cloud storage
            created_by_id: ID of user creating the file
            db: Database session to use for the operation
            metadata: Optional additional metadata

        Returns:
            Created File instance

        Raises:
            ValueError: If bucket doesn't exist
        """
        # Verify bucket exists
        bucket_query = select(Bucket).where(Bucket.id == bucket_id)
        bucket_result = await db.execute(bucket_query)
        bucket = bucket_result.scalar_one_or_none()

        if not bucket:
            raise ValueError(f"Bucket with ID {bucket_id} not found")

        # Extract file extension
        extension = os.path.splitext(filename)[1] if filename else None

        # Create file record
        file_record = File(
            filename=filename,
            original_filename=original_filename,
            extension=extension,
            bucket_id=bucket_id,
            file_size=file_size,
            content_type=content_type,
            storage_path=storage_path,
            created_by_id=created_by_id,
        )

        db.add(file_record)
        await db.commit()
        await db.refresh(file_record)

        logger.info(f"Created file record: {file_record.id} ({filename})")
        return file_record

    async def get_file_by_id(self, file_id: UUID, db: AsyncSession) -> File | None:
        """Get file by ID with related data.

        Args:
            file_id: ID of the file to retrieve
            db: Database session to use for the operation

        Returns:
            File instance if found, None otherwise
        """
        query = (
            select(File)
            .options(
                selectinload(File.bucket),
                selectinload(File.created_by),
                selectinload(File.updated_by),
            )
            .where(File.id == file_id)
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_file_by_id_or_404(self, file_id: UUID, db: AsyncSession) -> File:
        """Get file by ID or raise 404 HTTPException if not found.

        Args:
            file_id: ID of the file to retrieve
            db: Database session to use for the operation

        Returns:
            File instance

        Raises:
            HTTPException: 404 if file not found
        """
        file = await self.get_file_by_id(file_id, db)
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File with ID {file_id} not found",
            )
        return file

    async def get_files_by_bucket(
        self, bucket_id: UUID, db: AsyncSession, limit: int = 100, offset: int = 0
    ) -> list[File]:
        """Get files in a specific bucket.

        Args:
            bucket_id: ID of the bucket
            db: Database session to use for the operation
            limit: Maximum number of files to return
            offset: Number of files to skip

        Returns:
            List of File instances
        """
        query = (
            select(File)
            .options(selectinload(File.created_by), selectinload(File.updated_by))
            .where(File.bucket_id == bucket_id)
            .order_by(desc(File.created_at))
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_files_by_user(
        self, user_id: UUID, db: AsyncSession, limit: int = 100, offset: int = 0
    ) -> list[File]:
        """Get files created by a specific user.

        Args:
            user_id: ID of the user
            db: Database session to use for the operation
            limit: Maximum number of files to return
            offset: Number of files to skip

        Returns:
            List of File instances
        """
        query = (
            select(File)
            .options(selectinload(File.bucket), selectinload(File.created_by))
            .where(File.created_by_id == user_id)
            .order_by(desc(File.created_at))
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    async def search_files(
        self,
        query_text: str,
        db: AsyncSession,
        bucket_id: UUID | None = None,
        content_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[File]:
        """Search files by filename or metadata.

        Args:
            query_text: Text to search for in filename or original_filename
            db: Database session to use for the operation
            bucket_id: Optional bucket ID to limit search
            content_type: Optional content type filter
            limit: Maximum number of files to return
            offset: Number of files to skip

        Returns:
            List of File instances matching the search
        """
        query = select(File).options(
            selectinload(File.bucket), selectinload(File.created_by)
        )

        # Build search conditions
        conditions = []

        # Text search in filenames
        text_condition = File.filename.ilike(
            f"%{query_text}%"
        ) | File.original_filename.ilike(f"%{query_text}%")
        conditions.append(text_condition)

        # Optional filters
        if bucket_id:
            conditions.append(File.bucket_id == bucket_id)

        if content_type:
            conditions.append(File.content_type.ilike(f"{content_type}%"))

        # Apply conditions
        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(File.created_at)).limit(limit).offset(offset)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_file_metadata(
        self,
        file_id: UUID,
        updated_by_id: UUID,
        db: AsyncSession,
        metadata: dict | None = None,
        filename: str | None = None,
    ) -> File | None:
        """Update file metadata.

        Args:
            file_id: ID of the file to update
            updated_by_id: ID of user making the update
            db: Database session to use for the operation
            metadata: Optional new metadata to merge
            filename: Optional new filename

        Returns:
            Updated File instance if found, None otherwise
        """
        file_record = await self.get_file_by_id(file_id, db)
        if not file_record:
            return None

        # Update fields
        if filename:
            file_record.filename = filename

        if metadata:
            # Merge metadata instead of replacing
            current_metadata = file_record.metadata or {}
            current_metadata.update(metadata)
            file_record.metadata = current_metadata

        file_record.updated_by_id = updated_by_id
        file_record.updated_at = datetime.now(UTC)

        await db.commit()
        await db.refresh(file_record)

        logger.info(f"Updated file metadata: {file_record.id}")
        return file_record

    async def confirm_upload(self, file_id: UUID, db: AsyncSession) -> File:
        """Confirm that a file upload to storage was completed successfully.

        Updates the file status from 'pending' to 'available' after verifying
        the file exists in storage. This implements the "trust but verify" pattern
        for direct uploads.

        Args:
            file_id: ID of the file to confirm
            db: Database session to use for the operation

        Returns:
            Updated File instance with 'available' status

        Raises:
            HTTPException: 404 if file not found
            HTTPException: 400 if file is not in pending status
        """
        from fastapi import HTTPException, status

        # Get the file record
        file_record = await self.get_file_by_id(file_id, db)
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File with ID {file_id} not found",
            )

        # Verify the file is in pending status (not already confirmed)
        if file_record.status != "pending":
            logger.warning(
                f"Attempted to confirm non-pending file: {file_id} (status: {file_record.status})"
            )
            # Still return success if already available (idempotent)
            if file_record.status == "available":
                return file_record
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File is not in pending status (current: {file_record.status})",
            )

        # Update status to available
        file_record.status = "available"
        file_record.updated_at = datetime.now(UTC)

        await db.commit()
        await db.refresh(file_record)

        logger.info(f"Confirmed file upload: {file_record.id} - {file_record.filename}")
        return file_record

    async def delete_file_record(self, file_id: UUID, db: AsyncSession) -> bool:
        """Delete file metadata record from database.

        Note: This only deletes the database record. The actual file
        in cloud storage should be deleted separately using StorageService.

        Args:
            file_id: ID of the file to delete
            db: Database session to use for the operation

        Returns:
            True if file was deleted, False if not found
        """
        file_record = await self.get_file_by_id(file_id, db)
        if not file_record:
            return False

        await db.delete(file_record)
        await db.commit()

        logger.info(f"Deleted file record: {file_record.id}")
        return True

    async def get_file_stats(
        self, db: AsyncSession, bucket_id: UUID | None = None
    ) -> dict:
        """Get file statistics.

        Args:
            db: Database session to use for the operation
            bucket_id: Optional bucket ID to limit stats

        Returns:
            Dictionary containing file statistics
        """
        query = select(
            func.count(File.id).label("total_files"),
            func.sum(File.file_size).label("total_size"),
            func.avg(File.file_size).label("avg_size"),
        )

        if bucket_id:
            query = query.where(File.bucket_id == bucket_id)

        result = await db.execute(query)
        stats = result.first()

        return {
            "total_files": stats.total_files or 0,
            "total_size_bytes": stats.total_size or 0,
            "average_size_bytes": float(stats.avg_size or 0),
        }

    async def file_exists_in_db(self, file_id: UUID, db: AsyncSession) -> bool:
        """Check if file record exists in database.

        Args:
            file_id: ID of the file to check
            db: Database session to use for the operation

        Returns:
            True if file record exists, False otherwise
        """
        query = select(func.count(File.id)).where(File.id == file_id)
        result = await db.execute(query)
        count = result.scalar()
        return count > 0


# ---------------------------------------------------------------------- #
# Singleton helpers (following established pattern)                     #
# ---------------------------------------------------------------------- #


def get_file_service() -> FileService:
    """Create file service instance with dependency injection.

    FastAPI will cache this per request, so we don't create multiple instances
    within the same request context.

    Returns:
        FileService instance
    """
    return FileService()
