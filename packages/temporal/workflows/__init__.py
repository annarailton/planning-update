"""Temporal workflows package.

Workflows orchestrate activities into reliable, durable execution flows.
They handle retries, timeouts, and failures automatically.

Example usage:
    from packages.temporal import get_temporal_client, ProcessFileWorkflow

    client = await get_temporal_client()
    handle = await client.start_workflow(
        ProcessFileWorkflow.run,
        ProcessFileInput(file_id="...", bucket_name="...", user_id="..."),
        id=f"process-file-{file_id}",
        task_queue="default-tasks",
    )
    result = await handle.result()
"""

from .process_file import ProcessFileWorkflow

__all__ = [
    "ProcessFileWorkflow",
]
