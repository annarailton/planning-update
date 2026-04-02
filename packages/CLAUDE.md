# Shared Packages

Shared Python packages for backend and worker.

## packages/db

```python
from packages.db import User, File, Bucket, Job
from packages.db import get_db, Base, BaseModel
```

Add model: create in `models/` -> export in `__init__.py` -> import in `alembic/env.py` -> `pnpm db:create "msg"`

## packages/exceptions

```python
from packages.exceptions import (
    NotFoundError,      # 404
    ValidationError,    # 400
    ConflictError,      # 409
    ForbiddenError,     # 403
    ServiceUnavailableError,  # 503
)

raise NotFoundError("User", user_id)
```

## packages/redis

```python
from packages.redis import get_redis, init_redis
from packages.redis.pubsub import publish_event, Channels
from packages.redis.queue import JobQueue
```

## packages/storage

```python
from packages.storage import create_storage_service

storage = create_storage_service()
url = await storage.generate_signed_url(bucket, path, expires_in=3600)
```

## LLM Providers (openai, anthropic, gemini)

```python
import packages.openai as openai
import packages.anthropic as anthropic

response = await openai.chat([{"role": "user", "content": "Hi"}])
response = await anthropic.chat(messages, model="sonnet")

# Streaming
async for chunk in openai.stream_chat(messages):
    print(chunk, end="")

# Model registry
openai.get_model_ids()  # ['gpt-5-mini', 'gpt-5', ...]
openai.DEFAULT_MODEL    # 'gpt-5-mini'
```

## Other Packages

| Package             | Purpose                | Import                                                                                        |
| ------------------- | ---------------------- | --------------------------------------------------------------------------------------------- |
| `packages.llm`      | Shared LLM types       | `from packages.llm import LLMProvider, LLMResponse`                                           |
| `packages.temporal` | Workflow orchestration | `from packages.temporal import is_temporal_enabled, get_temporal_client, ProcessFileWorkflow` |
| `packages.langfuse` | LLM observability      | `from packages.langfuse import observe, observe_llm, is_langfuse_enabled`                     |
| `packages.logging`  | Colored logging        | `from packages.logging import get_logger, setup_logging`                                      |

## Constants Pattern

Define shared enums once in `packages/db/constants.py`, import everywhere, never redefine:

```python
# packages/db/constants.py (canonical)
class FileStatus(str, Enum):
    PENDING = "pending"
    AVAILABLE = "available"

from packages.db.constants import FileStatus
```
