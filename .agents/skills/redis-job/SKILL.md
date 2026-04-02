---
name: redis-job
description: Create a Redis Streams enqueue and worker handler flow. Use for background jobs, async processing, event consumers, or worker-backed tasks.
---

# Redis Job Handler

Use this when work should be enqueued in backend code and processed asynchronously in the worker.
Do not use this for immediate request/response tasks that should stay synchronous.

**Requires:** `"redis": true` and `"worker": true` in features.json

```
Backend (enqueue):              Worker (process):
├── services/my_service.py      ├── handlers/my_handler.py
└── routers/my_resource.py      └── handlers/__init__.py
```

## 1. Handler

```python
# services/worker/app/handlers/my_handler.py
from packages.redis.queue import ProgressCallback
from packages.logging import get_logger

logger = get_logger(__name__)

async def handle_my_job(payload: dict, on_progress: ProgressCallback) -> dict:
    file_id = payload["file_id"]
    user_id = payload["user_id"]

    logger.info(f"Processing job for file {file_id}")

    # Step 1: Download
    await on_progress(10, "Downloading file...")
    # ... do download

    # Step 2: Process
    await on_progress(50, "Processing...")
    # ... do processing

    # Step 3: Upload result
    await on_progress(90, "Uploading result...")
    # ... do upload

    await on_progress(100, "Complete")

    return {
        "status": "completed",
        "result_url": "https://...",
    }
```

## 2. Register Handler

```python
# services/worker/app/handlers/__init__.py
from handlers.my_handler import handle_my_job

HANDLERS = {
    # ... existing handlers
    "my_job": handle_my_job,
}
```

## 3. Enqueue from Backend

```python
# services/backend/app/services/my_service.py
from packages.redis.queue import JobQueue
from core.config import get_settings

settings = get_settings()

class MyService:
    def __init__(self):
        self.queue = JobQueue() if settings.is_redis_enabled else None

    async def start_processing(self, file_id: str, user_id: str) -> str:
        if not self.queue:
            raise ServiceUnavailableError("Redis not configured")

        job_id = await self.queue.create_job(
            job_type="my_job",
            payload={
                "file_id": file_id,
                "user_id": user_id,
            }
        )
        return job_id
```

## 4. API Endpoint

```python
# services/backend/app/routers/my_resource.py
from uuid import UUID
from fastapi import APIRouter
from services.my_service import MyService

router = APIRouter(prefix="/my-resources", tags=["my-resources"])

@router.post("/{id}/process")
async def start_processing(
    id: UUID,
    service: Annotated[MyService, Depends()],
    user: UserDep,
):
    job_id = await service.start_processing(str(id), user["user_id"])
    return {"job_id": job_id}
```

## 5. Frontend Progress Tracking

```typescript
// features/my-feature/hooks/useMyJob.ts
import { useJobStream } from "@/features/jobs/hooks/useJobStream";

export function useMyJob(jobId: string | null) {
  const { status, progress, progressMessage, result, error } =
    useJobStream(jobId);

  return {
    status, // 'pending' | 'processing' | 'completed' | 'failed'
    progress, // 0-100
    message: progressMessage,
    result, // Result data when completed
    error, // Error message if failed
  };
}
```

```typescript
// Usage in component
function ProcessingStatus({ jobId }: { jobId: string }) {
  const { status, progress, message, result } = useMyJob(jobId);

  if (status === 'completed') {
    return <div>Done! Result: {result.result_url}</div>;
  }

  return (
    <div>
      <progress value={progress} max={100} />
      <p>{message}</p>
    </div>
  );
}
```

## Error Handling

```python
# Errors in handler are caught by worker and stored in job result
async def handle_my_job(payload: dict, on_progress: ProgressCallback) -> dict:
    try:
        # ... processing
        return {"status": "completed"}
    except SomeExpectedError as e:
        raise  # Let worker handle it
```

## Key Patterns

- **Idempotent** -- jobs may retry; handler must be safe to run multiple times
- **Progress** -- report progress for long-running jobs
- **Cleanup** -- clean up partial results on failure
- **Timeouts** -- worker default 15min (configurable)
