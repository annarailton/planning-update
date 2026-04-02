# Worker Service

Background job processing via Redis Streams and Temporal workflows.

Requires: `"redis": true` in features.json

## Structure

```
app/
  handlers/     # Redis Stream job handlers
  main.py       # Entrypoint
```

## Redis Streams (Simple Jobs)

### Define Handler

```python
# handlers/__init__.py
from packages.redis.queue import ProgressCallback

async def handle_process_image(payload: dict, on_progress: ProgressCallback) -> dict:
    await on_progress(25, "Downloading...")
    await on_progress(75, "Optimizing...")
    return {"url": "https://..."}

HANDLERS["process_image"] = handle_process_image
```

### Start Job (Backend)

```python
from packages.redis.queue import JobQueue

queue = JobQueue()
job_id = await queue.create_job("process_image", {"image_id": "123"})
```

### Track Progress (Frontend)

```typescript
const { createJob } = useCreateJob();
const jobId = await createJob({ jobType: 'process_image', payload: {...} });

const { status, progress, result } = useJobStream(jobId);
```

## Temporal (Durable Workflows)

Requires: `"temporal": true` in features.json

### Define Workflow

```python
# packages/temporal/workflows/my_workflow.py
from temporalio import workflow
from temporalio.common import RetryPolicy

@workflow.defn
class ProcessFileWorkflow:
    @workflow.run
    async def run(self, input: ProcessFileInput) -> ProcessFileOutput:
        result = await workflow.execute_activity(
            download_file,
            input.file_id,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        return ProcessFileOutput(hash=result)
```

### Start Workflow (Backend)

```python
from services.temporal_service import get_temporal_service

temporal = await get_temporal_service()
if temporal.is_enabled:
    workflow_id = await temporal.start_process_file_workflow(
        file_id="...", bucket_name="...", user_id="..."
    )
```

### Temporal UI

`pnpm temporal:ui` -> http://localhost:8233

## Configuration

| Env Var          | Purpose                       |
| ---------------- | ----------------------------- |
| REDIS_URL        | Redis connection (required)   |
| TEMPORAL_ADDRESS | Temporal server (local/cloud) |
| TEMPORAL_API_KEY | Temporal Cloud auth           |

## Timeouts

Default: 15 min (max 60 min). Configure in `terraform/services/worker/variables.tf`.
