# Phase 2: ReelCraft Feature Migration

Migration of production-ready features from ReelCraft to fullstack-template.

> **Note:** For infrastructure refactoring (CI/CD simplification, reverse proxy, feature flags system), see `docs/TODO.md`. This document covers feature additions only.

---

## Status

| Phase | Description         | Status                                          |
| ----- | ------------------- | ----------------------------------------------- |
| 1     | Frontend Foundation | ✅ Done (logger, config exist)                  |
| 2     | Shared Packages     | ✅ Mostly done (redis, storage, temporal exist) |
| 3     | Bulk Upload         | Not started                                     |
| 4     | CI/CD Updates       | Superseded by `TODO.md` feature flags           |
| 5     | Documentation       | Ongoing                                         |

---

## TODO List

### Phase 1: Frontend Foundation ✅

- [x] **1.1** Create `services/frontend/app/src/shared/lib/logger.ts` - Centralized logger with levels
- [x] **1.2** Create `services/frontend/app/src/shared/lib/config.ts` - Centralized env config
- [x] **1.3** Update `environment/.env.frontend.example` - Add VITE_LOG_LEVEL

### Phase 2: Shared Packages ✅

- [x] **2.1** Create `packages/redis/` - Shared Redis client + pubsub + queue
- [x] **2.2** Create `packages/db/repositories/` - Repository pattern for data access
- [x] **2.3** Create `packages/storage/` - Storage abstraction layer
- [x] **2.4** Create `packages/temporal/` - Optional Temporal workflow engine

### Phase 3: Bulk Upload (Not Started)

- [ ] **3.1** Add batch schemas to `services/backend/app/schemas/files.py`
- [ ] **3.2** Add batch methods to `services/backend/app/services/file_service.py`
- [ ] **3.3** Add batch endpoints to `services/backend/app/routers/files.py`
- [ ] **3.4** Add batch methods to `services/frontend/.../fileService.ts`
- [ ] **3.5** Enhance `services/frontend/.../useFileUpload.ts` with batch support

### Phase 4: CI/CD Updates (Superseded)

> **Note:** These items are superseded by the feature flags system in `docs/TODO.md`.
> The new approach uses `features.json` to conditionally build/deploy services.

- [x] ~~**4.1** Update destroy-services.yml~~ → See TODO.md Phase 1
- [x] ~~**4.2** Update \_backend.yml~~ → Replaced by new deploy.yml
- [x] ~~**4.3** Update \_worker.yml~~ → Replaced by new deploy.yml
- [x] ~~**4.4** Update \_neon.yml~~ → Inlined into deploy.yml

### Phase 5: Documentation & Agents

- [x] **5.1** Update `CLAUDE.md` - Add new patterns and agents section
- [ ] **5.2** Create `.claude/agents/ux-critic.md` - UX analysis agent

---

## Detailed Specifications

### 1.1 Frontend Logger (`logger.ts`)

**Purpose:** Centralized logging with levels and namespaces

**Features:**

- Log levels: `debug`, `info`, `warn`, `error`, `silent`
- Namespace-based: `logger.create('FeatureName')`
- Methods: `debug()`, `info()`, `warn()`, `error()`, `time()`, `timeEnd()`
- Configurable via `VITE_LOG_LEVEL` env var
- Defaults: `debug` in dev, `error` in prod

**Usage:**

```typescript
import { logger } from "@/shared/lib/logger";
const log = logger.create("FileUpload");

log.debug("Starting upload", { fileCount: 5 });
log.info("Upload complete");
log.warn("Large file detected");
log.error("Upload failed", error);

log.time("uploadDuration");
// ... upload logic
log.timeEnd("uploadDuration"); // Logs: "[FileUpload] uploadDuration: 1234.5ms"
```

---

### 1.2 Frontend Config (`config.ts`)

**Purpose:** Centralized environment variable access with type safety

**Exports:**

```typescript
interface AppConfig {
  isDev: boolean;
  isProd: boolean;
  nodeEnv: string;
  backendUrl: string;
  clerkPublishableKey: string;
  debug: boolean;
  logLevel: LogLevel;
}

export const config: AppConfig;
export function getEnv(key: string, defaultValue?: string): string;
export function getBoolEnv(key: string, defaultValue?: boolean): boolean;
```

---

### 2.1 packages/redis

**Structure:**

```
packages/redis/
├── pyproject.toml
├── __init__.py          # Re-exports
├── client.py            # Singleton async client
├── pubsub.py            # Channel helpers + publish functions
└── queue.py             # JobQueue (Redis Streams)
```

**Key Functions:**

```python
# client.py
async def init_redis(redis_url: str) -> Redis
async def get_redis() -> Redis
def get_redis_or_none() -> Optional[Redis]
async def close_redis() -> None

# pubsub.py
def get_job_channel(job_id: UUID) -> str
def get_user_files_channel(user_id: UUID) -> str
async def publish_file_status(file_id: UUID, status: str, ...)
async def publish_file_complete(file_id: UUID, ...)
async def publish_file_error(file_id: UUID, error: str)

# queue.py
class JobQueue:
    async def enqueue(job_type: str, payload: dict, ...) -> str
    async def consume(consumer_name: str, ...) -> AsyncIterator[Job]
    async def acknowledge(job_id: str) -> None
```

---

### 2.2 packages/db/repositories

**Structure:**

```
packages/db/repositories/
├── __init__.py
├── base.py              # BaseRepository protocol
├── job_repository.py    # Job CRUD
├── file_repository.py   # File CRUD
└── user_repository.py   # User CRUD
```

**Pattern:**

```python
class JobRepository:
    @staticmethod
    async def create(db: AsyncSession, job_type: str, payload: dict, ...) -> Job

    @staticmethod
    async def get_by_id(db: AsyncSession, job_id: UUID) -> Optional[Job]

    @staticmethod
    async def get_by_user(db: AsyncSession, user_id: UUID, limit: int = 20, offset: int = 0) -> list[Job]

    @staticmethod
    async def update_status(db: AsyncSession, job_id: UUID, status: JobStatus, ...) -> Optional[Job]
```

**Rules:**

- Pure database operations only
- No business logic
- No external service calls
- Session passed as parameter

---

### 2.3 packages/storage

**Structure:**

```
packages/storage/
├── pyproject.toml
├── __init__.py
├── base.py              # Abstract BaseStorageService
├── constants.py         # Enums and constants
├── exceptions.py        # Custom exceptions
├── factory.py           # get_storage_service()
└── gcp.py               # GCPStorageService
```

**Abstract Interface:**

```python
class BaseStorageService(ABC):
    @abstractmethod
    async def upload_file(bucket_name: str, file_path: str, data: bytes, ...) -> str

    @abstractmethod
    async def download_file(bucket_name: str, file_path: str) -> bytes

    @abstractmethod
    async def delete_file(bucket_name: str, file_path: str) -> bool

    @abstractmethod
    async def file_exists(bucket_name: str, file_path: str) -> bool

    @abstractmethod
    async def generate_signed_url(bucket_name: str, file_path: str, expiration: timedelta, method: str = "GET", ...) -> str
```

---

### 2.4 packages/temporal (Optional)

**Structure:**

```
packages/temporal/
├── pyproject.toml
├── __init__.py
├── client.py            # TemporalConfig, get_temporal_client()
├── types/
│   └── file_types.py    # Input/Output dataclasses
└── workflows/
    └── process_batch_files.py
```

**Optional Loading:**

```python
# In __init__.py
try:
    from temporalio.client import Client
    TEMPORAL_AVAILABLE = True
except ImportError:
    TEMPORAL_AVAILABLE = False

def is_temporal_enabled() -> bool:
    return TEMPORAL_AVAILABLE and bool(os.getenv("TEMPORAL_API_KEY"))
```

**Workflow:**

```python
@workflow.defn
class ProcessBatchFilesWorkflow:
    """Process multiple files sequentially to avoid race conditions."""

    @workflow.run
    async def run(self, input: ProcessBatchFilesInput) -> ProcessBatchFilesOutput:
        results = []
        for file_id in input.file_ids:
            result = await workflow.execute_activity(
                process_file_activity,
                ProcessFileInput(file_id=file_id, ...),
                start_to_close_timeout=timedelta(minutes=5),
            )
            results.append(result)
        return ProcessBatchFilesOutput(results=results)
```

---

### 3.1-3.3 Bulk Upload Backend

**New Schemas:**

```python
class FileUploadMetadata(BaseModel):
    filename: str
    content_type: str
    file_size: int

class BatchFileUploadUrlRequest(BaseModel):
    bucket_id: UUID
    files: list[FileUploadMetadata]

class BatchFileUploadUrlResponseItem(BaseModel):
    index: int
    upload_url: str
    file_id: UUID
    storage_path: str

class BatchFileUploadUrlResponse(BaseModel):
    files: list[BatchFileUploadUrlResponseItem]
    expires_in: int  # seconds

class BatchConfirmRequest(BaseModel):
    file_ids: list[UUID]

class BatchConfirmResponseItem(BaseModel):
    file_id: UUID
    success: bool
    status: str  # "available", "failed"

class BatchConfirmResponse(BaseModel):
    files: list[BatchConfirmResponseItem]
    confirmed_count: int
    failed_count: int
```

**New Endpoints:**

```python
@router.post("/upload/batch-urls", response_model=BatchFileUploadUrlResponse)
async def get_batch_upload_urls(
    request: BatchFileUploadUrlRequest,
    token: AuthTokenDep,
    file_service: FileServiceDep,
    bucket_service: BucketServiceDep,
    storage_service: StorageServiceDep,
    db: DatabaseDep,
):
    """Get presigned URLs for multiple files in one request."""
    # Validate bucket access
    # Create file records in parallel
    # Generate presigned URLs in parallel (asyncio.gather)
    # Return batch response

@router.post("/upload/batch-confirm", response_model=BatchConfirmResponse)
async def batch_confirm_uploads(
    request: BatchConfirmRequest,
    token: AuthTokenDep,
    file_service: FileServiceDep,
    storage_service: StorageServiceDep,
    db: DatabaseDep,
):
    """Confirm multiple uploads completed successfully."""
    # Verify each file exists in storage
    # Update statuses to "available"
    # Optionally trigger Temporal workflow for media processing
    # Return confirmation results
```

---

### 3.4-3.5 Bulk Upload Frontend

**New Service Methods:**

```typescript
// fileService.ts

interface BatchUploadUrlRequest {
  bucket_id: string;
  files: Array<{
    filename: string;
    content_type: string;
    file_size: number;
  }>;
}

interface BatchUploadUrlResponse {
  files: Array<{
    index: number;
    upload_url: string;
    file_id: string;
    storage_path: string;
  }>;
  expires_in: number;
}

async function getBatchUploadUrls(
  request: BatchUploadUrlRequest,
): Promise<BatchUploadUrlResponse>;

async function uploadFilesToPresignedUrls(
  files: Array<{ file: File; uploadUrl: string }>,
  onProgress?: (fileIndex: number, progress: number) => void,
): Promise<Array<{ success: boolean; error?: string }>>;

async function batchConfirmUploads(
  fileIds: string[],
): Promise<BatchConfirmResponse>;

async function uploadFilesBatch(
  bucketId: string,
  files: File[],
  onProgress?: (fileIndex: number, progress: number) => void,
): Promise<BatchUploadResult>;
```

**Enhanced Hook:**

```typescript
// useFileUpload.ts

interface UseFileUploadOptions {
  useBatchUpload?: boolean; // Enable batch mode
  onUploadComplete?: (file: UploadedFile) => void;
  onAllUploadsComplete?: (files: UploadedFile[]) => void;
  onUploadError?: (file: File, error: Error) => void;
}

function useFileUpload(bucketId: string, options?: UseFileUploadOptions) {
  // ... existing state ...

  const uploadFilesBatch = async (files: File[]) => {
    // 1. Get batch presigned URLs
    // 2. Upload all files in parallel with per-file progress
    // 3. Batch confirm all uploads
    // 4. Update state and call callbacks
  };

  return {
    // ... existing returns ...
    uploadFilesBatch,
  };
}
```

---

### 4.1 Destroy Services Workflow

**Changes to `.github/workflows/destroy-services.yml`:**

```yaml
name: Destroy Services

on:
  workflow_dispatch:
    inputs:
      branch_name:
        description: "Branch name to destroy"
        required: true
        type: string
      confirm_protected_branch:
        description: "I confirm I want to delete main/staging resources (required for protected branches)"
        required: false
        type: boolean
        default: false

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Validate protected branch confirmation
        if: |
          (inputs.branch_name == 'main' || inputs.branch_name == 'staging') &&
          inputs.confirm_protected_branch != true
        run: |
          echo "::error::You must check the confirmation box to delete main or staging resources"
          echo "This is a destructive action that cannot be undone."
          exit 1

      - name: Confirm destruction
        run: |
          echo "Proceeding with destruction of branch: ${{ inputs.branch_name }}"
          if [[ "${{ inputs.branch_name }}" == "main" || "${{ inputs.branch_name }}" == "staging" ]]; then
            echo "::warning::DESTROYING PROTECTED BRANCH RESOURCES"
          fi
```

---

### 4.2-4.3 Conditional Redis/Temporal in CI/CD

**Add to `_backend.yml` and `_worker.yml`:**

```yaml
- name: Configure Redis
  id: redis
  run: |
    # Priority: 1) Input, 2) Secret, 3) Backend state lookup
    if [ -n "${{ inputs.redis_url }}" ]; then
      echo "Using Redis URL from input"
      echo "redis_url=${{ inputs.redis_url }}" >> $GITHUB_OUTPUT
    elif [ -n "${{ secrets.REDIS_URL }}" ]; then
      echo "Using Redis URL from secret"
      echo "redis_url=${{ secrets.REDIS_URL }}" >> $GITHUB_OUTPUT
    else
      echo "Will look up Redis URL from backend state"
      echo "redis_url=" >> $GITHUB_OUTPUT
    fi

- name: Configure Temporal (if enabled)
  id: temporal
  run: |
    if [ -n "${{ secrets.TEMPORAL_API_KEY }}" ]; then
      echo "Temporal is enabled"
      echo "enabled=true" >> $GITHUB_OUTPUT
      echo "TF_VAR_temporal_api_key=${{ secrets.TEMPORAL_API_KEY }}" >> $GITHUB_ENV
      echo "TF_VAR_temporal_namespace=${{ vars.TEMPORAL_NAMESPACE || 'default' }}" >> $GITHUB_ENV
      echo "TF_VAR_temporal_address=${{ vars.TEMPORAL_ADDRESS || 'localhost:7233' }}" >> $GITHUB_ENV
    else
      echo "Temporal is disabled (no API key)"
      echo "enabled=false" >> $GITHUB_OUTPUT
    fi

- name: Lookup backend state (if needed)
  if: steps.redis.outputs.redis_url == '' || steps.temporal.outputs.enabled == 'true'
  run: |
    # Initialize terraform and read outputs
    cd terraform/services/backend
    terraform init -backend-config="prefix=${{ inputs.branch_name }}"

    if [ -z "${{ steps.redis.outputs.redis_url }}" ]; then
      REDIS_URL=$(terraform output -raw redis_url 2>/dev/null || echo "")
      echo "TF_VAR_redis_url=$REDIS_URL" >> $GITHUB_ENV
    fi

    if [ "${{ steps.temporal.outputs.enabled }}" == "true" ]; then
      TEMPORAL_TASK_QUEUE=$(terraform output -raw temporal_task_queue 2>/dev/null || echo "default-queue")
      echo "TF_VAR_temporal_task_queue=$TEMPORAL_TASK_QUEUE" >> $GITHUB_ENV
    fi
```

---

### 5.1 CLAUDE.md Updates

**Add sections:**

```markdown
## Frontend Patterns

### Logging

Use the centralized logger instead of console.log:
\`\`\`typescript
import { logger } from '@/shared/lib/logger';
const log = logger.create('MyFeature');

log.debug('Debug info'); // Dev only
log.info('Important info');
log.warn('Warning');
log.error('Error', error);
\`\`\`

### Configuration

Use the centralized config instead of import.meta.env:
\`\`\`typescript
import { config } from '@/shared/lib/config';

if (config.isDev) { ... }
const apiUrl = config.backendUrl;
\`\`\`

## Shared Packages

### packages/redis

Shared Redis client for backend and worker:

- `init_redis()`, `get_redis()`, `close_redis()` - Client lifecycle
- `publish_file_status()`, `publish_job_progress()` - Pub/sub events
- `JobQueue` - Redis Streams job queue

### packages/storage

Storage abstraction layer:

- `BaseStorageService` - Abstract interface
- `GCPStorageService` - GCP implementation
- `get_storage_service()` - Factory function

### packages/db/repositories

Repository pattern for data access:

- `JobRepository` - Job CRUD
- `FileRepository` - File CRUD
- `UserRepository` - User CRUD

### packages/temporal (Optional)

Temporal workflow engine (requires TEMPORAL_API_KEY):

- `get_temporal_client()` - Get Temporal client
- `ProcessBatchFilesWorkflow` - Batch file processing

## Available Agents

- **ux-critic**: Analyze user flows for friction and usability issues
```

---

### 5.2 UX-Critic Agent

**File:** `.claude/agents/ux-critic.md`

**Content:**

- Analysis framework (First Impressions, Cognitive Load, Friction Points, etc.)
- Severity levels (Critical, Major, Minor, Enhancement)
- User persona checks (Impatient, Confused, Power User, Mobile)
- Output format template
- 10 UX heuristics

---

## File Summary

### New Files (25)

| File                                                 | Purpose             |
| ---------------------------------------------------- | ------------------- |
| `services/frontend/app/src/shared/lib/logger.ts`     | Centralized logger  |
| `services/frontend/app/src/shared/lib/config.ts`     | Centralized config  |
| `packages/redis/pyproject.toml`                      | Package config      |
| `packages/redis/__init__.py`                         | Re-exports          |
| `packages/redis/client.py`                           | Async Redis client  |
| `packages/redis/pubsub.py`                           | Pub/sub helpers     |
| `packages/redis/queue.py`                            | Job queue (Streams) |
| `packages/db/repositories/__init__.py`               | Exports             |
| `packages/db/repositories/base.py`                   | Base protocol       |
| `packages/db/repositories/job_repository.py`         | Job CRUD            |
| `packages/db/repositories/file_repository.py`        | File CRUD           |
| `packages/db/repositories/user_repository.py`        | User CRUD           |
| `packages/storage/pyproject.toml`                    | Package config      |
| `packages/storage/__init__.py`                       | Re-exports          |
| `packages/storage/base.py`                           | Abstract interface  |
| `packages/storage/constants.py`                      | Enums/constants     |
| `packages/storage/exceptions.py`                     | Custom exceptions   |
| `packages/storage/factory.py`                        | Factory function    |
| `packages/storage/gcp.py`                            | GCP implementation  |
| `packages/temporal/pyproject.toml`                   | Package config      |
| `packages/temporal/__init__.py`                      | Re-exports          |
| `packages/temporal/client.py`                        | Temporal client     |
| `packages/temporal/types/file_types.py`              | Type definitions    |
| `packages/temporal/workflows/process_batch_files.py` | Batch workflow      |
| `.claude/agents/ux-critic.md`                        | UX analysis agent   |

### Modified Files (12)

| File                                            | Changes                    |
| ----------------------------------------------- | -------------------------- |
| `services/backend/app/schemas/files.py`         | Add batch schemas          |
| `services/backend/app/services/file_service.py` | Add batch methods          |
| `services/backend/app/routers/files.py`         | Add batch endpoints        |
| `services/backend/app/core/redis.py`            | Re-export from package     |
| `services/frontend/.../fileService.ts`          | Add batch methods          |
| `services/frontend/.../useFileUpload.ts`        | Add batch support          |
| `environment/.env.frontend.example`             | Add VITE_LOG_LEVEL         |
| `environment/.env.backend.example`              | Add Temporal vars          |
| `.github/workflows/destroy-services.yml`        | Add confirmation           |
| `.github/workflows/_backend.yml`                | Conditional Redis/Temporal |
| `.github/workflows/_worker.yml`                 | Conditional Redis/Temporal |
| `CLAUDE.md`                                     | Add new sections           |

---

## Implementation Order

1. Frontend Foundation (1.1, 1.2, 1.3)
2. packages/storage (2.3)
3. packages/redis (2.1)
4. packages/db/repositories (2.2)
5. packages/temporal (2.4)
6. Bulk Upload Backend (3.1, 3.2, 3.3)
7. Bulk Upload Frontend (3.4, 3.5)
8. CI/CD Updates (4.1, 4.2, 4.3, 4.4)
9. Documentation (5.1, 5.2)
