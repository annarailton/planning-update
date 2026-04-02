---
name: temporal-workflow
description: Create a Temporal workflow with activities, registration, and calling service code. Auto-loads for durable execution, long-running orchestration, retries, or resumable jobs.
disable-model-invocation: false
user-invocable: true
---

# Temporal Workflow

Use this for durable orchestration that needs retries, resumability, or long-running state.
Do not use this for simple background jobs that fit the Redis worker pattern.

**Requires:** `"temporal": true` in features.json

```
packages/temporal/
├── workflows/
│   └── my_workflow.py      # Workflow definition
├── activities/
│   └── my_activities.py    # Activity functions
└── __init__.py             # Export workflow + activities
```

## 1. Activities

```python
# packages/temporal/activities/my_activities.py
from temporalio import activity
from dataclasses import dataclass

@dataclass
class MyInput:
    file_id: str
    user_id: str

@dataclass
class MyOutput:
    result: str

@activity.defn
async def fetch_data(input: MyInput) -> dict:
    """Activities do the actual work. Keep them focused."""
    # Do work here
    return {"data": "..."}

@activity.defn
async def process_data(data: dict) -> MyOutput:
    # Process and return
    return MyOutput(result="done")
```

## 2. Workflow

```python
# packages/temporal/workflows/my_workflow.py
from temporalio import workflow
from temporalio.common import RetryPolicy
from datetime import timedelta

with workflow.unsafe.imports_passed_through():
    from packages.temporal.activities.my_activities import (
        fetch_data, process_data, MyInput, MyOutput
    )

@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self, input: MyInput) -> MyOutput:
        # Execute activities with retry policy
        data = await workflow.execute_activity(
            fetch_data,
            input,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        result = await workflow.execute_activity(
            process_data,
            data,
            start_to_close_timeout=timedelta(minutes=10),
        )

        return result
```

## 3. Export

```python
# packages/temporal/__init__.py
from packages.temporal.workflows.my_workflow import MyWorkflow
from packages.temporal.activities.my_activities import (
    fetch_data, process_data, MyInput, MyOutput
)
```

## 4. Register in Worker

```python
# services/worker/app/main.py
from packages.temporal import MyWorkflow, fetch_data, process_data

# Add to worker registration
workflows=[MyWorkflow],
activities=[fetch_data, process_data],
```

## 5. Start from Backend

```python
# services/backend/app/services/my_service.py
from services.temporal_service import get_temporal_service

async def start_my_workflow(file_id: str, user_id: str):
    temporal = await get_temporal_service()
    if not temporal.is_enabled:
        raise ServiceUnavailableError("Temporal not configured")

    workflow_id = f"my-workflow-{file_id}"
    handle = await temporal.client.start_workflow(
        MyWorkflow.run,
        MyInput(file_id=file_id, user_id=user_id),
        id=workflow_id,
        task_queue="default-tasks",
    )
    return workflow_id
```

## Key Patterns

- **Activities** = side effects (API calls, DB, files)
- **Workflows** = orchestration (no side effects, deterministic)
- **Timeouts** = always set `start_to_close_timeout`
- **Retry** = `RetryPolicy` for transient failures
- **Idempotency** = workflow ID should be deterministic for retries
