"""Files API router for file management.

Provides file management endpoints with upload, download, and metadata operations.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path as PathLib
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Path,
    Query,
    UploadFile,
    status,
)

from core.config import get_settings, get_storage_bucket_name
from core.dependencies import (
    AuthTokenDep,
    BucketServiceDep,
    DatabaseDep,
    FileServiceDep,
    StorageServiceDep,
)
from core.logging import get_logger
from schemas.files import (
    BatchConfirmRequest,
    BatchConfirmResponse,
    BatchConfirmResponseItem,
    BatchFileUploadUrlRequest,
    BatchFileUploadUrlResponse,
    BatchFileUploadUrlResponseItem,
    FileDownloadResponse,
    FileListResponse,
    FileResponse,
    FileStatsResponse,
    FileUpdateRequest,
    FileUploadUrlRequest,
    FileUploadUrlResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/search", response_model=FileListResponse)
async def search_files(
    q: str = Query(None, description="Search query to match against filename"),
    bucket_id: UUID = Query(None, description="Filter by bucket ID"),
    limit: int = Query(100, ge=1, le=1000, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    _: AuthTokenDep = None,
    file_service: FileServiceDep = None,
    db: DatabaseDep = None,
):
    """Search for files by name.

    **Query parameters:**
    - **q**: Search query to match against filename (case-insensitive partial match)
    - **bucket_id**: Filter results by specific bucket
    - **limit**: Maximum number of results (1-1000, default: 100)
    - **offset**: Number of results to skip for pagination

    **Returns:** List of matching files with metadata
    """
    files = await file_service.search_files(
        query_text=q or "", bucket_id=bucket_id, limit=limit, offset=offset, db=db
    )

    # Get total count (simplified for now)
    total = len(files)

    return FileListResponse(
        files=[FileResponse.from_file_model(file) for file in files],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=FileStatsResponse)
async def get_file_stats(
    bucket_id: UUID = Query(None, description="Filter by bucket ID"),
    _: AuthTokenDep = None,
    file_service: FileServiceDep = None,
    db: DatabaseDep = None,
):
    """Get file statistics.

    **Query parameters:**
    - **bucket_id**: Get stats for specific bucket only

    **Returns:** Statistics including total files, total size, and file type breakdown
    """
    stats = await file_service.get_file_stats(bucket_id=bucket_id, db=db)

    return FileStatsResponse(**stats)


@router.get("/", response_model=FileListResponse)
async def list_files(
    bucket_id: UUID = Query(None, description="Filter by bucket ID"),
    limit: int = Query(100, ge=1, le=1000, description="Number of files to return"),
    offset: int = Query(0, ge=0, description="Number of files to skip"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    _: AuthTokenDep = None,
    file_service: FileServiceDep = None,
    db: DatabaseDep = None,
):
    """List all files with pagination.

    **Query parameters:**
    - **bucket_id**: Filter by specific bucket
    - **limit**: Maximum number of files to return (1-1000, default: 100)
    - **offset**: Number of files to skip for pagination
    - **sort_by**: Field to sort by (default: created_at)
    - **sort_order**: Sort order - asc or desc (default: desc)

    **Returns:** Paginated list of files with metadata
    """
    # Get files based on bucket_id if provided, otherwise get all files for the user
    if bucket_id:
        files = await file_service.get_files_by_bucket(
            bucket_id=bucket_id, limit=limit, offset=offset, db=db
        )
    else:
        # For now, get all files (you might want to filter by user in production)
        files = await file_service.search_files(
            query_text="", bucket_id=None, limit=limit, offset=offset, db=db
        )

    # Get total count
    total = len(files)  # Simple count for now

    return FileListResponse(
        files=[FileResponse.from_file_model(file) for file in files],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/upload/url", response_model=FileUploadUrlResponse)
async def get_upload_url(
    request: FileUploadUrlRequest,
    token: AuthTokenDep = None,
    file_service: FileServiceDep = None,
    bucket_service: BucketServiceDep = None,
    storage_service: StorageServiceDep = None,
    db: DatabaseDep = None,
):
    """Generate a presigned URL for direct file upload to cloud storage.

    **Trust-But-Verify Pattern Implementation:**
    This endpoint implements a secure file upload pattern that balances performance with security:

    - **Trust**: We create a database record and presigned URL before the actual upload
    - **But**: The presigned URL is time-limited and restricted to specific operations
    - **Verify**: Upload must be confirmed via `/upload/confirm/{file_id}` to mark as available

    This pattern prevents the backend from being a bottleneck for large file uploads while
    maintaining control over what gets uploaded (file size limits, content types, etc.).

    **Process:**
    1. Creates a file record in the database with 'pending' status (Trust)
    2. Generates a time-limited presigned URL for Google Cloud Storage
    3. Returns the URL and file ID for the client to complete the upload
    4. Client uploads directly to GCS using the presigned URL (Performance)
    5. Client confirms upload completion via `/upload/confirm/{file_id}` (Verify)

    **Request body:**
    - **bucket_id**: Target bucket for the file
    - **filename**: Name for the uploaded file
    - **content_type**: MIME type of the file
    - **file_size**: Size of the file in bytes

    **Returns:** Presigned upload URL, file ID, and upload instructions
    """
    # Validate bucket exists
    await bucket_service.get_bucket_by_id_or_404(request.bucket_id, db)

    # Validate file type
    file_service.validate_file_type(request.filename, request.content_type)

    # Generate unique file ID
    file_id = uuid4()

    # Create storage path with original name, timestamp, and short UUID for better identification
    # Format: {original_name_sanitized}_{timestamp}_{uuid_short}.{ext}
    import re

    # Extract filename without extension and extension
    file_path = PathLib(request.filename)
    file_extension = file_path.suffix.lower()
    base_filename = file_path.stem

    # Sanitize filename - remove special chars, limit length
    sanitized_name = re.sub(r"[^a-zA-Z0-9\-_]", "_", base_filename)[
        :30
    ]  # Limit to 30 chars

    # Create timestamp (shorter format)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    # Use first 8 chars of UUID for brevity
    short_uuid = str(file_id)[:8]

    # Combine into storage path (no prefix needed - bucket already indicates environment)
    storage_filename = f"{sanitized_name}_{timestamp}_{short_uuid}{file_extension}"

    # Store the filename as-is since buckets are already environment-specific
    storage_path_full = storage_filename

    # Get user from token
    user = token.get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found in token"
        )

    # Create file record with pending status (store full path with prefix)
    file_record = await file_service.create_file_record(
        filename=request.filename,
        original_filename=request.filename,
        bucket_id=request.bucket_id,
        file_size=request.file_size,
        content_type=request.content_type,
        storage_path=storage_path_full,  # Store the full path with prefix
        created_by_id=user.id,
        db=db,
        metadata=None,
    )

    # Generate presigned upload URL
    get_settings()
    bucket_name = get_storage_bucket_name()
    expiration = timedelta(hours=1)

    upload_url = await storage_service.generate_signed_url(
        bucket_name=bucket_name,
        file_path=storage_filename,  # Pass filename without prefix (will be added by storage service)
        expiration=expiration,
        method="PUT",
        content_type=request.content_type,
    )

    return FileUploadUrlResponse(
        file_id=file_record.id,  # Return the actual database record ID, not the storage filename ID
        upload_url=upload_url,
        expires_in=int(expiration.total_seconds()),
        storage_path=storage_path_full,  # Return the full path that was stored in DB
    )


@router.post("/upload/confirm/{file_id}", response_model=FileResponse)
async def confirm_upload(
    file_id: UUID = Path(..., description="UUID of the file to confirm"),
    _: AuthTokenDep = None,
    file_service: FileServiceDep = None,
    storage_service: StorageServiceDep = None,
    db: DatabaseDep = None,
):
    """Confirm that a direct upload to cloud storage was completed.

    **Trust-But-Verify Pattern - Verification Step:**
    This is the final step in our secure upload pattern. After the client uploads
    directly to storage using the presigned URL, this endpoint:

    1. Verifies the file actually exists in Google Cloud Storage
    2. Updates the database record from 'pending' to 'available' status
    3. Makes the file visible in file listings and available for download

    Without this confirmation, files remain in 'pending' status and are not
    accessible, preventing abuse of presigned URLs or incomplete uploads.

    **Path parameters:**
    - **file_id**: UUID of the file (obtained from `/upload/url` response)

    **Returns:** Updated file metadata with confirmed status
    """
    # Get file record
    file = await file_service.get_file_by_id_or_404(file_id, db)

    # Verify file exists in storage
    get_settings()
    bucket_name = get_storage_bucket_name()

    exists = await storage_service.file_exists(
        bucket_name=bucket_name, file_path=file.storage_path
    )

    if not exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File not found in storage. Please retry the upload.",
        )

    # Update file status to available
    file = await file_service.confirm_upload(file_id, db)

    # Convert to response model
    return FileResponse.from_file_model(file)


# =============================================================================
# Batch Upload Endpoints
# =============================================================================


@router.post("/upload/batch-urls", response_model=BatchFileUploadUrlResponse)
async def get_batch_upload_urls(
    request: BatchFileUploadUrlRequest,
    token: AuthTokenDep = None,
    file_service: FileServiceDep = None,
    bucket_service: BucketServiceDep = None,
    storage_service: StorageServiceDep = None,
    db: DatabaseDep = None,
):
    """Generate presigned URLs for multiple files in a single request.

    This endpoint optimizes bulk uploads by:
    1. Creating all file records in the database
    2. Generating all presigned URLs in parallel
    3. Returning all URLs in a single response

    After receiving the URLs, clients should:
    1. Upload all files to their respective URLs in parallel
    2. Call `/upload/batch-confirm` with all file IDs

    **Request body:**
    - **bucket_id**: Target bucket for all files
    - **files**: List of file metadata (filename, content_type, file_size)

    **Returns:** List of presigned URLs with file IDs
    """
    import asyncio
    import re

    # Validate bucket exists
    await bucket_service.get_bucket_by_id_or_404(request.bucket_id, db)

    # Get user from token
    user = token.get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found in token"
        )

    # Get storage config
    bucket_name = get_storage_bucket_name()
    expiration = timedelta(hours=1)

    # Prepare all files and generate URLs in parallel
    response_items = []

    async def prepare_file(index: int, file_meta):
        # Validate file type
        file_service.validate_file_type(file_meta.filename, file_meta.content_type)

        # Generate unique file ID
        file_id = uuid4()

        # Create storage path
        file_path = PathLib(file_meta.filename)
        file_extension = file_path.suffix.lower()
        base_filename = file_path.stem
        sanitized_name = re.sub(r"[^a-zA-Z0-9\-_]", "_", base_filename)[:30]
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        short_uuid = str(file_id)[:8]
        storage_filename = f"{sanitized_name}_{timestamp}_{short_uuid}{file_extension}"

        # Create file record
        file_record = await file_service.create_file_record(
            filename=file_meta.filename,
            original_filename=file_meta.filename,
            bucket_id=request.bucket_id,
            file_size=file_meta.file_size,
            content_type=file_meta.content_type,
            storage_path=storage_filename,
            created_by_id=user.id,
            db=db,
            metadata=None,
        )

        # Generate presigned URL
        upload_url = await storage_service.generate_signed_url(
            bucket_name=bucket_name,
            file_path=storage_filename,
            expiration=expiration,
            method="PUT",
            content_type=file_meta.content_type,
        )

        return BatchFileUploadUrlResponseItem(
            index=index,
            upload_url=upload_url,
            file_id=file_record.id,
            storage_path=storage_filename,
        )

    # Process all files in parallel
    tasks = [prepare_file(i, file_meta) for i, file_meta in enumerate(request.files)]
    response_items = await asyncio.gather(*tasks)

    return BatchFileUploadUrlResponse(
        files=list(response_items),
        expires_in=int(expiration.total_seconds()),
    )


@router.post("/upload/batch-confirm", response_model=BatchConfirmResponse)
async def batch_confirm_uploads(
    request: BatchConfirmRequest,
    token: AuthTokenDep = None,
    file_service: FileServiceDep = None,
    storage_service: StorageServiceDep = None,
    db: DatabaseDep = None,
):
    """Confirm multiple file uploads completed successfully.

    This endpoint verifies that all files were uploaded to storage
    and updates their status from 'pending' to 'available'.

    **Request body:**
    - **file_ids**: List of file UUIDs to confirm

    **Returns:** Confirmation results for each file
    """
    bucket_name = get_storage_bucket_name()
    results = []
    confirmed_count = 0
    failed_count = 0

    for file_id in request.file_ids:
        try:
            # Get file record
            file = await file_service.get_file_by_id(file_id, db)
            if not file:
                results.append(
                    BatchConfirmResponseItem(
                        file_id=file_id,
                        success=False,
                        status="not_found",
                    )
                )
                failed_count += 1
                continue

            # Verify file exists in storage
            exists = await storage_service.file_exists(
                bucket_name=bucket_name, file_path=file.storage_path
            )

            if not exists:
                results.append(
                    BatchConfirmResponseItem(
                        file_id=file_id,
                        success=False,
                        status="not_in_storage",
                    )
                )
                failed_count += 1
                continue

            # Update file status to available
            await file_service.confirm_upload(file_id, db)

            results.append(
                BatchConfirmResponseItem(
                    file_id=file_id,
                    success=True,
                    status="available",
                )
            )
            confirmed_count += 1

        except Exception as e:
            logger.error(f"Error confirming file {file_id}: {e}")
            results.append(
                BatchConfirmResponseItem(
                    file_id=file_id,
                    success=False,
                    status="error",
                )
            )
            failed_count += 1

    return BatchConfirmResponse(
        files=results,
        confirmed_count=confirmed_count,
        failed_count=failed_count,
    )


@router.post(
    "/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED
)
async def upload_file(
    background_tasks: BackgroundTasks,
    bucket_id: UUID = Form(..., description="Target bucket ID"),
    file: UploadFile = File(..., description="File to upload"),
    metadata: str = Form(None, description="Optional JSON metadata"),
    token: AuthTokenDep = None,
    file_service: FileServiceDep = None,
    bucket_service: BucketServiceDep = None,
    storage_service: StorageServiceDep = None,
    db: DatabaseDep = None,
):
    """Upload a file through the backend server.

    For smaller files, this endpoint handles the entire upload process.
    For larger files, consider using `/upload/url` for direct browser uploads.

    **Form data:**
    - **bucket_id**: Target bucket for the file
    - **file**: File content (multipart/form-data)
    - **metadata**: Optional JSON string with custom metadata

    **Returns:** File metadata including ID and storage location
    """
    # Validate bucket exists
    await bucket_service.get_bucket_by_id_or_404(bucket_id, db)

    # Validate file type and size
    file_service.validate_file_type(file.filename, file.content_type)
    if file.size:
        file_service.validate_file_size(file.size)

    # Parse metadata if provided
    file_metadata = {}
    if metadata:
        try:
            file_metadata = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON in metadata field",
            )

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Generate file ID and storage path
    file_id = uuid4()
    file_extension = PathLib(file.filename).suffix.lower()
    storage_path = f"{file_id}{file_extension}"

    # Get user from token
    user = token.get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found in token"
        )

    # Create file record
    file_record = await file_service.create_file_record(
        filename=file.filename,
        original_filename=file.filename,
        bucket_id=bucket_id,
        file_size=file_size,
        content_type=file.content_type,
        storage_path=storage_path,
        created_by_id=user.id,
        db=db,
        metadata=file_metadata,
    )

    # Upload to storage
    get_settings()
    bucket_name = get_storage_bucket_name()

    await storage_service.upload_file(
        bucket_name=bucket_name,
        file_path=storage_path,
        file_data=file_content,
        content_type=file.content_type,
    )

    return FileResponse.from_file_model(file_record)


@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: UUID = Path(..., description="UUID of the file to retrieve"),
    _: AuthTokenDep = None,
    file_service: FileServiceDep = None,
    db: DatabaseDep = None,
):
    """Get file metadata by ID.

    **Path parameters:**
    - **file_id**: UUID of the file

    **Returns:** File metadata including storage location and timestamps
    """
    file = await file_service.get_file_by_id_or_404(file_id, db)
    return FileResponse.from_orm(file)


@router.put("/{file_id}", response_model=FileResponse)
async def update_file(
    file_id: UUID = Path(..., description="UUID of the file to update"),
    update_data: FileUpdateRequest = ...,
    _: AuthTokenDep = None,
    file_service: FileServiceDep = None,
    db: DatabaseDep = None,
):
    """Update file metadata.

    **Path parameters:**
    - **file_id**: UUID of the file to update

    **Request body:**
    - **filename**: New filename (optional)
    - **metadata**: Updated metadata object (optional)

    **Returns:** Updated file metadata
    """
    # Get existing file
    file = await file_service.get_file_by_id_or_404(file_id, db)

    # Update fields
    update_dict = update_data.dict(exclude_unset=True)

    if "filename" in update_dict:
        # Validate new filename has same extension
        old_ext = PathLib(file.filename).suffix.lower()
        new_ext = PathLib(update_dict["filename"]).suffix.lower()
        if old_ext != new_ext:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot change file extension from {old_ext} to {new_ext}",
            )

    # Update file record
    file = await file_service.update_file(
        file_id=file_id,
        update_data=update_dict,
        updated_by_id=uuid4(),  # TODO: Use actual user ID from auth
        db=db,
    )

    return FileResponse.from_orm(file)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: UUID = Path(..., description="UUID of the file to delete"),
    _: AuthTokenDep = None,
    file_service: FileServiceDep = None,
    storage_service: StorageServiceDep = None,
    db: DatabaseDep = None,
):
    """Delete a file from storage and database.

    **Path parameters:**
    - **file_id**: UUID of the file to delete

    **Returns:** 204 No Content on success
    """
    # Get file record
    file = await file_service.get_file_by_id_or_404(file_id, db)

    # Delete from storage
    get_settings()
    bucket_name = get_storage_bucket_name()

    try:
        await storage_service.delete_file(
            bucket_name=bucket_name, file_path=file.storage_path
        )
    except Exception as e:
        logger.warning(f"Failed to delete file from storage: {e}")
        # Continue with database deletion even if storage deletion fails

    # Delete from database
    await file_service.delete_file_record(file_id, db)


@router.get("/{file_id}/download", response_model=FileDownloadResponse)
async def download_file(
    file_id: UUID = Path(..., description="UUID of the file to download"),
    _: AuthTokenDep = None,
    file_service: FileServiceDep = None,
    storage_service: StorageServiceDep = None,
    db: DatabaseDep = None,
):
    """Get a signed download URL for a file.
    
    **Process:**
    1. Looks up file metadata in database
    2. Generates a temporary signed URL (expires in 1 hour)
    3. Returns URL for direct download from Google Cloud Storage
    
    **Path parameters:**
    - **file_id**: UUID of the file (obtained from upload response or file listing)
    
    **Example using curl:**
    ```bash
    curl -X GET "http://localhost:8000/api/files/{file_id}/download" \
      -H "Authorization: Bearer your-token"
    
    # Use the returned signed_url to download the file
    curl -o downloaded-file.pdf "https://storage.googleapis.com/signed-url..."
    ```
    
    **Returns:** Temporary signed URL valid for 1 hour
    """
    try:
        # Get file info
        file = await file_service.get_file_by_id_or_404(file_id, db)

        # Use the file's storage path
        file_path = file.storage_path

        # Get configuration
        get_settings()
        bucket_name = get_storage_bucket_name()

        # Generate signed URL
        expiration = timedelta(hours=1)
        signed_url = await storage_service.generate_signed_url(
            bucket_name=bucket_name,
            file_path=file_path,
            expiration=expiration,
            method="GET",
        )

        return FileDownloadResponse(
            signed_url=signed_url, expires_in_seconds=int(expiration.total_seconds())
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error generating download URL for file {file_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the download URL",
        )
