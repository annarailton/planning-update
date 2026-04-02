"""Temporal worker factory.

Creates and configures a Temporal worker with all workflows and activities.
The worker polls the configured task queue and executes workflows/activities.

Usage:
    from temporal import create_temporal_worker
    from packages.temporal import get_temporal_client

    client = await get_temporal_client()
    worker = await create_temporal_worker(client)
    await worker.run()  # Blocks until shutdown
"""

import logging
from datetime import timedelta
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import (
    SandboxedWorkflowRunner,
    SandboxRestrictions,
)

from packages.temporal import TemporalConfig

# Pre-import packages that will be used in workflows to avoid cold-start delays
# This ensures they're loaded before the sandbox tries to import them
import packages.temporal.activities
import packages.temporal.activities.file_activities
import packages.temporal.types

# Import workflows and activities
from packages.temporal.workflows import ProcessFileWorkflow
from packages.temporal.activities import (
    # Progress publishing activities
    publish_progress,
    publish_complete,
    publish_error,
    # File processing activities
    download_file,
    calculate_hash,
    extract_metadata,
    generate_thumbnail,
    update_file_status,
)

logger = logging.getLogger(__name__)


async def create_temporal_worker(client: Client) -> Worker:
    """Create a Temporal worker with all workflows and activities registered.

    Args:
        client: Connected Temporal client

    Returns:
        Configured Temporal worker (not yet started)

    Usage:
        client = await get_temporal_client()
        worker = await create_temporal_worker(client)
        await worker.run()  # Blocks until shutdown
    """
    config = TemporalConfig.from_env()

    logger.info(f"Creating Temporal worker for task queue: {config.task_queue}")

    # Concurrency settings for parallel activity execution
    max_concurrent_activities = 10  # Adjust based on workload
    max_concurrent_workflows = 5  # Adjust based on memory/CPU

    # Configure sandbox with relaxed restrictions for packages that are pre-imported
    # This avoids deadlock detection issues on cold start when imports are slow
    workflow_runner = SandboxedWorkflowRunner(
        restrictions=SandboxRestrictions.default.with_passthrough_modules(
            "packages",
            "packages.temporal",
            "packages.temporal.activities",
            "packages.temporal.activities.file_activities",
            "packages.temporal.types",
            "packages.temporal.progress",
            "packages.redis",
            "packages.redis.pubsub",
        )
    )

    worker = Worker(
        client,
        task_queue=config.task_queue,
        max_concurrent_activities=max_concurrent_activities,
        max_concurrent_workflow_tasks=max_concurrent_workflows,
        workflow_runner=workflow_runner,
        workflows=[
            ProcessFileWorkflow,
            # Add more workflows here as you create them
        ],
        activities=[
            # Progress publishing activities (for SSE streaming)
            publish_progress,
            publish_complete,
            publish_error,
            # File processing activities
            download_file,
            calculate_hash,
            extract_metadata,
            generate_thumbnail,
            update_file_status,
            # Add more activities here as you create them
        ],
    )

    logger.info(
        f"Temporal worker created for task queue '{config.task_queue}'. "
        f"Concurrency: {max_concurrent_activities} activities, {max_concurrent_workflows} workflows"
    )

    return worker
