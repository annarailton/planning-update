"""File processing workflow.

This workflow orchestrates the complete file processing pipeline:
1. Download file from cloud storage
2. Calculate content hash for deduplication
3. Extract metadata (dimensions, duration, etc.)
4. Generate thumbnail
5. Update database with results

Each step is an activity that can be independently retried on failure.
Progress is published to Redis for real-time SSE streaming.
"""

import logging
from datetime import timedelta

from temporalio import workflow

# Import activities with sandbox isolation
with workflow.unsafe.imports_passed_through():
    from packages.temporal.activities import (
        download_file,
        calculate_hash,
        extract_metadata,
        generate_thumbnail,
        update_file_status,
        publish_progress,
        publish_complete,
        publish_error,
    )
    from packages.temporal.activities.file_activities import (
        DownloadFileInput,
        CalculateHashInput,
        ExtractMetadataInput,
        GenerateThumbnailInput,
        UpdateFileStatusInput,
        PublishProgressInput,
        PublishCompleteInput,
        PublishErrorInput,
        FAST_RETRY_POLICY,
        NETWORK_RETRY_POLICY,
        HEAVY_RETRY_POLICY,
    )
    from packages.temporal.types import ProcessFileInput, ProcessFileOutput


TOTAL_STEPS = 5


@workflow.defn
class ProcessFileWorkflow:
    """Workflow for processing a single file.

    This workflow handles the complete lifecycle of file processing,
    from download to database update. Each step is durable and will
    be retried on failure.

    Usage:
        client = await get_temporal_client()
        handle = await client.start_workflow(
            ProcessFileWorkflow.run,
            ProcessFileInput(
                file_id="abc123",
                bucket_name="my-bucket",
                user_id="user456",
            ),
            id=f"process-file-abc123",
            task_queue="default-tasks",
        )
        result = await handle.result()
    """

    @workflow.run
    async def run(self, input: ProcessFileInput) -> ProcessFileOutput:
        """Execute the file processing workflow.

        Args:
            input: File processing parameters

        Returns:
            Processing result with status and metadata
        """
        workflow_id = f"process-file-{input.file_id}"
        workflow.logger.info(f"Starting file processing for {input.file_id}")

        async def _publish(step: int, message: str, activity_name: str = None):
            """Helper to publish progress."""
            progress = int((step / TOTAL_STEPS) * 100)
            await workflow.execute_activity(
                publish_progress,
                PublishProgressInput(
                    workflow_id=workflow_id,
                    progress=progress,
                    message=message,
                    activity_name=activity_name,
                    step=step,
                    total_steps=TOTAL_STEPS,
                ),
                start_to_close_timeout=timedelta(seconds=5),
            )

        try:
            # Step 1: Download file from cloud storage
            await _publish(1, "Downloading file...", "download_file")
            download_result = await workflow.execute_activity(
                download_file,
                DownloadFileInput(
                    file_id=input.file_id,
                    bucket_name=input.bucket_name,
                    gcs_path=f"uploads/{input.user_id}/{input.file_id}",
                ),
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=NETWORK_RETRY_POLICY,
                heartbeat_timeout=timedelta(minutes=2),
            )

            # Step 2: Calculate content hash for deduplication
            await _publish(2, "Calculating content hash...", "calculate_hash")
            hash_result = await workflow.execute_activity(
                calculate_hash,
                CalculateHashInput(local_path=download_result.local_path),
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=FAST_RETRY_POLICY,
            )

            # Step 3: Extract metadata
            await _publish(3, "Extracting metadata...", "extract_metadata")
            metadata_result = await workflow.execute_activity(
                extract_metadata,
                ExtractMetadataInput(
                    local_path=download_result.local_path,
                    file_type="image",  # TODO: Detect from file
                ),
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=FAST_RETRY_POLICY,
            )

            # Step 4: Generate thumbnail
            await _publish(4, "Generating thumbnail...", "generate_thumbnail")
            thumbnail_result = await workflow.execute_activity(
                generate_thumbnail,
                GenerateThumbnailInput(
                    local_path=download_result.local_path,
                    output_path=f"/tmp/{input.file_id}_thumb.jpg",
                ),
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=HEAVY_RETRY_POLICY,
            )

            # Step 5: Update database with success
            await _publish(5, "Updating database...", "update_file_status")
            await workflow.execute_activity(
                update_file_status,
                UpdateFileStatusInput(
                    file_id=input.file_id,
                    status="available",
                    content_hash=hash_result.content_hash,
                    thumbnail_url=f"thumbnails/{input.file_id}_thumb.jpg",
                    metadata=metadata_result.metadata,
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=FAST_RETRY_POLICY,
            )

            workflow.logger.info(f"File {input.file_id} processed successfully")

            # Publish completion
            result = {
                "file_id": input.file_id,
                "status": "available",
                "content_hash": hash_result.content_hash,
                "thumbnail_url": f"thumbnails/{input.file_id}_thumb.jpg",
            }
            await workflow.execute_activity(
                publish_complete,
                PublishCompleteInput(workflow_id=workflow_id, result=result),
                start_to_close_timeout=timedelta(seconds=5),
            )

            return ProcessFileOutput(
                file_id=input.file_id,
                status="available",
                content_hash=hash_result.content_hash,
                thumbnail_url=f"thumbnails/{input.file_id}_thumb.jpg",
                metadata=metadata_result.metadata,
            )

        except Exception as e:
            workflow.logger.error(f"File {input.file_id} processing failed: {e}")

            # Publish error
            await workflow.execute_activity(
                publish_error,
                PublishErrorInput(workflow_id=workflow_id, error=str(e)),
                start_to_close_timeout=timedelta(seconds=5),
            )

            # Update database with failure status
            await workflow.execute_activity(
                update_file_status,
                UpdateFileStatusInput(
                    file_id=input.file_id,
                    status="failed",
                    error_message=str(e),
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=FAST_RETRY_POLICY,
            )

            return ProcessFileOutput(
                file_id=input.file_id,
                status="failed",
                error_message=str(e),
            )
