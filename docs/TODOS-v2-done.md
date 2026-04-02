# 🗺️ Template v2 Roadmap (COMPLETED)

> **Status:** ✅ All v2 items completed. For current work (CI/CD simplification, feature flags, reverse proxy), see `docs/TODO.md`.

Tracking the evolution to a robust, job-oriented architecture with real-time progress and enterprise observability.

---

## 📁 Current Structure (v2 - Implemented)

```text
.
├── services/
│   ├── backend/                    # FastAPI (Python/uv)
│   │   └── app/
│   │       ├── core/               # Security, deps, config
│   │       ├── middleware/         # Request middleware
│   │       ├── routers/            # API endpoints (incl. jobs SSE)
│   │       ├── schemas/            # Pydantic schemas
│   │       ├── services/           # Business logic
│   │       │   ├── llm/            # Multi-provider LLM service
│   │       │   ├── job_service.py  # Job orchestration
│   │       │   └── job_queue.py    # Redis Stream producer
│   │       └── tests/              # Pytest suite
│   │
│   ├── frontend/                   # React + Vite (pnpm)
│   │   └── app/src/
│   │       ├── features/           # Domain modules
│   │       │   ├── jobs/           # Job UI (hooks, components)
│   │       │   └── ...
│   │       ├── pages/              # Route-level views
│   │       └── shared/
│   │           └── components/
│   │               └── animations/ # Motion, R3F, Lottie
│   │
│   └── worker/                     # Background job processor
│       └── app/
│           ├── main.py             # FastAPI + lifespan consumer
│           ├── processor.py        # Job consumer loop
│           ├── handlers/           # Job type handlers
│           └── services/           # Redis + DB operations
│
├── packages/
│   └── db/                         # Shared database package
│       ├── alembic/                # Centralized migrations
│       ├── models/                 # SQLAlchemy ORM (User, File, Job, etc.)
│       ├── base.py                 # Base class
│       └── connection.py           # DB connection utilities
│
├── terraform/                      # Centralized IaC
│   ├── modules/                    # Reusable modules
│   │   ├── cloud-run/
│   │   ├── gcs/
│   │   └── artifact-registry/
│   └── services/                   # Service-specific configs
│       ├── backend/
│       ├── frontend/
│       └── worker/                 # + Redis Cloud database
│
├── environment/                    # .env files
├── scripts/                        # setup.sh, webhook-tunnel.sh
├── .github/workflows/              # CI/CD pipelines
│   ├── _backend.yml, _frontend.yml, _worker.yml, _neon.yml
│   ├── deploy-all.yml, destroy-services.yml
│   └── *-deploy.yml triggers
├── docker-compose.yml              # Local dev (+ redis, redis-insight, worker)
└── package.json                    # Root task runner
```

---

## 📊 Gap Analysis

| Category                        | Have | To Add |
| ------------------------------- | :--: | :----: |
| API (FastAPI/Cloud Run)         |  ✅  |   —    |
| Frontend (React/Vite/Cloud Run) |  ✅  |   —    |
| Database (Neon/Postgres)        |  ✅  |   —    |
| Storage (GCS)                   |  ✅  |   —    |
| Auth (Clerk)                    |  ✅  |   —    |
| AI (Multi-provider LLM)         |  ✅  |   —    |
| CI/CD (GitHub Actions)          |  ✅  |   —    |
| IaC (Terraform)                 |  ✅  |   —    |
| Animation & 3D (Motion/R3F)     |  ✅  |   —    |
| Redis (Queue/Cache/Pub-Sub)     |  ✅  |   —    |
| Worker Service                  |  ✅  |   —    |
| SSE Progress                    |  ✅  |   —    |
| Shared DB Package               |  ✅  |   —    |
| LLM Tracing (Langfuse)          |  ✅  |   —    |
| **Setup Wizard (Web)**          |  ✅  |   —    |

---

## 🏗️ Target Structure (v2) — ✅ ACHIEVED

The target structure has been fully implemented. See "Current Structure" above.

---

## ✅ Implementation Checklist (Priority Order)

### 1. Frontend Animation & 3D Stack

Modern animation and 3D capabilities for a polished UI. **Independent, quick win.**

**Packages to install:**

```bash
# Upgrade framer-motion to motion
pnpm remove framer-motion && pnpm add motion

# 3D Graphics
pnpm add three @react-three/fiber @react-three/drei @react-three/postprocessing

# Lottie Animations
pnpm add @lottiefiles/dotlottie-react

# TypeScript types
pnpm add -D @types/three
```

**Tasks:**

- [x] Migrate `framer-motion` to `motion` (update imports from `framer-motion` → `motion/react`).
- [x] Install React Three Fiber + Drei + Postprocessing for 3D.
- [x] Install dotLottie for vector animations.
- [x] Create `shared/components/animations/` directory for reusable animated components.
- [x] Add example 3D component (e.g., animated hero, 3D logo).
- [x] Add page transition animations with Motion.
- [x] Document animation patterns in `CLAUDE.md`.

### 2. Shared Database Package (`packages/db`)

**Foundation for worker service.** Extract DB code so both backend and worker can share it.

- [x] Create `packages/db/` directory structure.
- [x] Extract `Base` class and naming conventions to `packages/db/base.py`.
- [x] Extract connection utilities (`create_async_engine`, `sessionmaker`, `get_db`) to `packages/db/connection.py`.
- [x] Move models from `services/backend/app/models/` to `packages/db/models/`.
- [x] Update `services/backend/` imports to use `packages.db`.
- [x] Centralize migrations in `packages/db/alembic/` (single source of truth).
- [x] Configure `packages/db` as installable dependency (pip install -e or Python path).
- [x] Add `Job` model for worker queue tracking.
- [x] Ensure worker service can import from `packages.db`.
- [x] Update `CLAUDE.md` with new database package documentation.

### 3. Multi-Provider LLM Service

**Independent.** Replace `openai_service.py` with unified LLM service supporting multiple providers.

**Structure:**

```
services/llm/
├── base.py           # Protocol + types (LLMMessage, LLMResponse, LLMConfig)
├── factory.py        # Provider factory with availability checks
├── __init__.py       # Unified LLMService entry point
└── providers/
    ├── openai.py     # OpenAI (native SDK)
    ├── anthropic.py  # Anthropic (native SDK)
    ├── gemini.py     # Google Gemini (native SDK)
    └── azure_openai.py
```

**Tasks:**

- [x] Create `services/llm/base.py` with `LLMProvider` protocol and response types.
- [x] Create `services/llm/providers/openai.py` (thin wrapper around `AsyncOpenAI`).
- [x] Create `services/llm/providers/anthropic.py` (thin wrapper around `AsyncAnthropic`).
- [x] Create `services/llm/providers/gemini.py` (thin wrapper around `google-genai`).
- [x] Create `services/llm/factory.py` with lazy init + API key availability checks.
- [x] Create `services/llm/__init__.py` with unified `LLMService`.
- [x] Add provider API keys to config: `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, etc.
- [x] Add new packages to `pyproject.toml`: `anthropic`, `google-genai`.
- [x] Add `/api/llm/providers` endpoint to list available providers/models.
- [x] Add `/api/llm/chat` and `/api/llm/generate` unified endpoints.
- [x] Migrate existing code to use `LLMService` instead of `OpenAIService`.
- [x] Delete old `openai_service.py` after migration complete.

### 4. Local Dev Setup (Docker Compose)

**Depends on:** `packages/db` existing. Add Redis and worker skeleton for local development.

- [x] **docker-compose.yml**: Add `redis` service (Redis 8.4).
- [x] **docker-compose.yml**: Add `redis-insight` service (port 5540).
- [x] **docker-compose.yml**: Add `worker` service skeleton (imports `packages.db`).
- [x] Create `services/worker/` with Dockerfile, pyproject.toml, and app skeleton.
- [x] Update root `package.json` with worker/redis commands.

### 5. Terraform Refactor

**Production infrastructure.** Modularize Terraform and add Redis Cloud.

- [x] Move Terraform to `terraform/` directory (modules + services structure).
- [x] Create `terraform/modules/cloud-run/` module.
- [x] Create `terraform/modules/gcs/` module.
- [x] Create `terraform/modules/artifact-registry/` module.
- [x] Redis Cloud Pro subscription created manually (shared across projects).
- [x] Create `terraform/services/backend/` using modules.
- [x] Create `terraform/services/frontend/` using modules.
- [x] Create `terraform/services/worker/` using modules + Redis database per environment.
- [x] Remove `local-exec` from Terraform - Docker builds now in GitHub Actions.
- [ ] Add `REDISCLOUD_ACCESS_KEY`, `REDISCLOUD_SECRET_KEY` to GitHub Secrets.
- [ ] Add `REDIS_SUBSCRIPTION_ID` to GitHub Secrets (after first `_shared-infra.yml` run).

### 6. CI/CD Improvements

**Depends on:** Terraform refactor being complete.

- [x] Update `_backend.yml` - separate build/deploy jobs, new Terraform paths.
- [x] Update `_frontend.yml` - separate build/deploy jobs, new Terraform paths.
- [x] Add `_worker.yml` reusable workflow.
- [x] Add `worker-deploy.yml` trigger workflow.
- [x] Update `deploy-all.yml` with worker service.
- [x] Update `destroy-services.yml` with worker service.

### 7. Worker Service (Full Implementation) ✅

**Depends on:** `packages/db`, Redis, CI/CD ready.

- [x] Implement wake-on-job pattern in worker (lifespan manager + consumer loop).
- [x] Add blocking consumer with configurable timeout (5s default).
- [x] Add stuck job reclaim logic (`xautoclaim` with 60s timeout).
- [x] Add progress publisher (Redis Pub/Sub to `job:{job_id}` channel).
- [x] **Backend**: Add `services/job_queue.py` + `services/job_service.py` (job queue producer).
- [x] **Backend**: Add `routers/jobs.py` with SSE progress stream endpoint.

### 8. Frontend Progress UI ✅

**Depends on:** Worker service + SSE endpoints.

- [x] Create `features/jobs/hooks/useJobStream.ts` (SSE hook with auto-reconnect).
- [x] Create `features/jobs/hooks/useCreateJob.ts` (job creation hook).
- [x] Create `features/jobs/components/JobTracker.tsx` (animated progress bar with Motion).
- [x] Create `features/jobs/components/JobCreator.tsx` (job submission UI).
- [x] Create `features/jobs/components/JobsList.tsx` (job history).
- [x] Full integration from creation to real-time progress tracking.

### 9. Observability (Langfuse) ✅

**Easy SDK integration.** Optional - only initializes if API keys are set.

- [x] Add Langfuse env vars: `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_HOST`.
- [x] Install `langfuse` package in backend.
- [x] Create `langfuse_service.py` with optional initialization pattern.
- [x] Integrate Langfuse with LLM Service (trace_name, trace_user_id, etc. params).
- [x] Add Langfuse env vars to `environment/.env.backend.example`.
- [x] Add Langfuse env vars to Terraform + GitHub Actions workflow.

### 10. Setup Wizard (Web-Based)

**Replace CLI setup with a user-friendly local web interface.**

Current `scripts/setup.sh` is CLI-only with many prompts - users have reported it's not user-friendly.

**Proposed approach:**

```bash
pnpm setup              # Opens http://localhost:4321/setup
```

**Architecture:**

```
scripts/setup-wizard/
├── server.js          # Minimal Node server (~100 lines, no dependencies)
├── index.html         # Single page wizard UI
└── wizard.js          # Frontend logic
```

**Server endpoints (thin bridge to local system):**

- `GET /api/check-prereqs` → runs `which docker`, `which gcloud`, etc.
- `POST /api/validate` → validates API keys, GCP project access
- `POST /api/write-env` → writes .env files
- `POST /api/run-command` → executes setup commands

**Tasks:**

- [x] Create `scripts/setup-wizard/server.js` using Node built-in `http` + `child_process` (no npm dependencies).
- [x] Create `scripts/setup-wizard/index.html` with step-by-step wizard UI.
- [x] Create `scripts/setup-wizard/wizard.js` for frontend logic.
- [x] Add step-by-step wizard with progress checkpoints.
- [x] Validate inputs before proceeding (API key format, project existence).
- [x] Generate `.env` files on completion.
- [x] Show clear error messages with fix suggestions.
- [x] Support resume from checkpoint (localStorage).
- [ ] Add "copy to clipboard" for commands user needs to run manually.
- [x] Add `pnpm setup` script to root `package.json`.

**Checkpoints:**

1. Prerequisites check (Docker, pnpm, gcloud CLI)
2. GCP project selection/creation
3. API keys input (Clerk, OpenAI, etc.)
4. Database setup (Neon)
5. Local environment generation
6. Docker startup and health check

### 11. Scripts + Docs ✅

**Last.** Document everything.

- [x] Update `README.md` with new architecture.
- [x] Update `CLAUDE.md` with new patterns (LLM Service, animations, worker).
- [ ] Add visual architecture diagram (PNG/SVG) - text diagrams exist in CLAUDE.md.

---

## 🔑 New Environment Variables

```bash
# Redis (Local)
REDIS_URL=redis://localhost:6379

# Redis Cloud (Production - for Terraform)
REDISCLOUD_ACCESS_KEY=...                 # Redis Cloud API account key
REDISCLOUD_SECRET_KEY=...                 # Redis Cloud API secret key

# Worker
WORKER_URL=http://worker:8080             # Docker network
WORKER_URL=https://worker-xxx.run.app     # Cloud Run

# Langfuse (Observability)
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com  # or https://us.cloud.langfuse.com

# LLM Providers (only set the ones you need)
OPENAI_API_KEY=sk-...                     # Already exists
ANTHROPIC_API_KEY=sk-ant-...              # For Claude models
GEMINI_API_KEY=...                        # For Gemini models
AZURE_OPENAI_API_KEY=...                  # For Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/
```

---

## 🌏 Deployment Regions

Single-region deployments. Set the `REGION` GitHub repository variable to deploy to a specific region.

| Region    | GCP Region ID          | Location   |
| --------- | ---------------------- | ---------- |
| Singapore | `asia-southeast1`      | Singapore  |
| London    | `europe-west2`         | London, UK |
| Sydney    | `australia-southeast1` | Sydney, AU |

**How to change region:**

1. Go to repository **Settings → Variables and secrets → Actions**
2. Add/update variable: `REGION=australia-southeast1`
3. Deploy - all resources (Cloud Run, Artifact Registry, GCS) will be created in that region

**Database note:** Neon PostgreSQL is separate from GCP. Choose a Neon region close to your GCP region:

- Singapore → Neon `ap-southeast-1`
- London → Neon `eu-west-2`
- Sydney → Neon `ap-southeast-2`

---

## 🎯 Summary

| Component                    | Status  | Purpose                                                     |
| ---------------------------- | ------- | ----------------------------------------------------------- |
| `services/llm/`              | ✅ Done | Multi-provider LLM service (OpenAI, Anthropic, Gemini)      |
| `services/worker/`           | ✅ Done | Background job processor (Redis Streams, stale job reclaim) |
| `packages/db/`               | ✅ Done | Shared models + connection utils for backend/worker         |
| `terraform/modules/`         | ✅ Done | Reusable infra (cloud-run, gcs, artifact-registry)          |
| `terraform/services/worker/` | ✅ Done | Worker infra + Redis Cloud database per environment         |
| SSE progress endpoint        | ✅ Done | Real-time job updates to frontend                           |
| Frontend jobs UI             | ✅ Done | Job creation, tracking, progress visualization              |
| Motion + R3F + Lottie        | ✅ Done | Modern animations & 3D graphics for frontend                |
| Langfuse                     | ✅ Done | LLM call tracing & analytics (optional)                     |
| Setup Wizard (Web)           | ✅ Done | Web UI at localhost:4321 via `pnpm setup`                   |

---

## 🚀 What's Left Before First Deploy

1. **Get Redis Cloud API Keys:**
   - Go to https://app.redislabs.com → Account → Access Management → API Keys
   - Create new API key and copy both Access Key and Secret Key

2. **Add GitHub Secrets:**

   ```bash
   gh secret set REDISCLOUD_ACCESS_KEY --body "your-access-key"
   gh secret set REDISCLOUD_SECRET_KEY --body "your-secret-key"
   gh secret set REDIS_SUBSCRIPTION_ID --body "3056171"  # Tomoro AI shared subscription
   ```

3. **Push to main/staging** → CI/CD creates Redis database automatically

**Note:** Subscription `#3056171` ("Tomoro AI") is the shared Redis Cloud Pro subscription for all Tomoro projects.
