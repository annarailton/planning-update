# Fullstack Template

Build production AI apps at lightning speed. A pre-wired fullstack architecture with React, FastAPI, PostgreSQL, Redis, and multi-provider LLM support. Deploy to Google Cloud Platform in under 10 minutes.

[![Deploy Status](https://github.com/tomoro-ai/fullstack-template/actions/workflows/deploy-all.yml/badge.svg)](https://github.com/tomoro-ai/fullstack-template/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

### Core (always included)

- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS
- **Backend**: FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic
- **Database**: PostgreSQL (Neon) with branch-based development
- **Storage**: Google Cloud Storage with presigned URLs
- **Auth**: Clerk authentication with webhook sync
- **Deployment**: Google Cloud Run (serverless containers)
- **CI/CD**: GitHub Actions with automatic deployments
- **IaC**: Terraform for all infrastructure
- **Environments**: Production, staging, and branch-based development

### Optional (choose during setup)

| Feature       | Default | Description                                                                 |
| ------------- | ------- | --------------------------------------------------------------------------- |
| **Redis**     | Off     | Caching, pub/sub, session storage via Redis Cloud                           |
| **Worker**    | Off     | Background job processing via Redis Streams (requires Redis)                |
| **Temporal**  | Off     | Durable workflow orchestration with retries and visibility (requires Redis) |
| **OpenAI**    | On      | GPT models via `packages/openai`                                            |
| **Anthropic** | Off     | Claude models via `packages/anthropic`                                      |
| **Gemini**    | Off     | Gemini models via `packages/gemini`                                         |
| **Langfuse**  | Off     | LLM observability and tracing                                               |

Features are selected in the setup wizard and stored in `features.json`. They control which services run locally, which containers are built, which API routes are registered, and which infrastructure is deployed.

---

## Quick Start

### 1. Create Your Repository

This is a GitHub template repository. Click the green **"Use this template"** button above, or:

[![Use this template](https://img.shields.io/badge/Use%20this%20template-238636?style=for-the-badge&logo=github&logoColor=white)](https://github.com/tomoro-ai/fullstack-template/generate)

1. Click **"Use this template"** → **"Create a new repository"**
2. Name your repository and set visibility
3. Click **"Create repository"**

### 2. Run Setup Wizard

```bash
# Clone your new repository
git clone https://github.com/yourusername/your-new-repo.git
cd your-new-repo

# Install dependencies
pnpm install

# Run the setup wizard (opens web UI at localhost:3456)
pnpm run setup
```

The wizard guides you through:

1. Prerequisites check (Node.js, Docker, gcloud CLI)
2. Repository and app name
3. Feature selection (Redis, Worker, Temporal, LLM providers)
4. Google Cloud Platform project and region
5. Service account credentials
6. Neon database connection
7. Clerk authentication
8. AI providers (OpenAI, Anthropic, Gemini) and Langfuse
9. Temporal Cloud (if enabled in features)

### 2b. Pre-commit [Optional]

To get for common linting and formatting errors before files are committed, one can use `pre-commit`.

Make sure you have pre-commit either globally or within a project's configs with `brew install pre-commit` or `uv add pre-commit`.

Run `pre-commit install` to install the pre-commit hook settings.

One each commit, it will run `ruff format` with package `isort` and also lint your frontend app. This will hopefully avoid lengthy github action failures.

### 3. Start Development

After setup completes:

```bash
# Start all services
pnpm dev
```

Your app is running at:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs
- **Redis Insight**: http://localhost:5540
- **Temporal UI**: http://localhost:8233 (if Temporal enabled)
- **Storage UI**: http://localhost:4443

---

## Project Structure

```
.
├── services/
│   ├── backend/           # FastAPI backend service
│   │   └── app/
│   │       ├── core/      # Configuration, settings
│   │       ├── routers/   # API endpoints
│   │       ├── services/  # Business logic
│   │       ├── schemas/   # Pydantic schemas
│   │       └── tests/     # Backend tests
│   │
│   ├── frontend/          # React SPA
│   │   └── app/src/
│   │       ├── features/  # Feature modules (auth, files, temporal)
│   │       ├── shared/    # Shared utilities and components
│   │       └── pages/     # Route components
│   │
│   └── worker/            # Background job worker
│       └── app/
│           └── handlers/  # Job handlers (Redis Streams + Temporal)
│
├── packages/              # Shared Python packages
│   ├── db/               # Database models, migrations
│   ├── redis/            # Redis client, pub/sub, queues
│   ├── storage/          # GCS storage with presigned URLs
│   ├── openai/           # OpenAI wrapper with retry
│   ├── anthropic/        # Anthropic wrapper with retry
│   ├── gemini/           # Gemini wrapper with retry
│   ├── llm/              # Shared LLM types
│   ├── temporal/         # Temporal workflows and activities
│   ├── langfuse/         # LLM observability (optional)
│   ├── logging/          # Shared logging config
│   └── exceptions/       # Shared domain exceptions
│
├── terraform/
│   ├── modules/          # Reusable Terraform modules
│   └── services/         # Per-service infrastructure
│       ├── backend/
│       ├── frontend/
│       └── worker/
│
├── scripts/
│   ├── setup-wizard/     # Web-based setup UI
│   ├── setup.sh          # CLI setup script
│   └── setup-env.sh      # Environment file setup
│
├── .github/workflows/    # CI/CD pipelines
├── environment/          # Environment files (.env.*)
└── docker-compose.yml    # Local development
```

---

## Development Commands

```bash
# ═══════════════════════════════════════════════════════════════════════
# Development
# ═══════════════════════════════════════════════════════════════════════
pnpm dev                  # Start all services (frontend, backend, worker, temporal)
pnpm dev:build            # Rebuild and start
pnpm down                 # Stop all services
pnpm clean                # Stop and remove volumes
pnpm reset                # Full cleanup including Docker system prune
pnpm logs                 # View all logs

# ═══════════════════════════════════════════════════════════════════════
# Database (models in packages/db/)
# ═══════════════════════════════════════════════════════════════════════
pnpm db:migrate           # Run migrations
pnpm db:create "name"     # Create new migration
pnpm db:rollback          # Rollback last migration
pnpm db:reset             # Reset database (down to base, then up)
pnpm db:history           # Show migration history
pnpm db:erd               # Generate ERD diagram

# ═══════════════════════════════════════════════════════════════════════
# Testing
# ═══════════════════════════════════════════════════════════════════════
pnpm test:backend         # Run backend tests
pnpm test:backend:unit    # Unit tests only
pnpm test:backend:cov     # Tests with coverage
pnpm test:frontend        # Run frontend tests

# ═══════════════════════════════════════════════════════════════════════
# Worker & Redis
# ═══════════════════════════════════════════════════════════════════════
pnpm worker:logs          # View worker logs
pnpm worker:shell         # Shell into worker container
pnpm redis:cli            # Redis CLI
pnpm redis:ui             # Open Redis Insight (localhost:5540)

# ═══════════════════════════════════════════════════════════════════════
# Temporal (if enabled)
# ═══════════════════════════════════════════════════════════════════════
pnpm temporal:ui          # Open Temporal UI (localhost:8233)
pnpm temporal:logs        # View Temporal server logs

# ═══════════════════════════════════════════════════════════════════════
# Storage
# ═══════════════════════════════════════════════════════════════════════
pnpm storage:ui           # Open storage UI
pnpm storage:list         # List files in storage
```

---

## Deployment

### Automatic Deployment

GitHub Actions automatically deploy on push:

| Branch         | Environment | Description                |
| -------------- | ----------- | -------------------------- |
| `main`         | Production  | Full production deployment |
| `staging`      | Staging     | Pre-production testing     |
| Other branches | Development | Isolated dev environment   |

### Workflows

| Workflow      | Trigger            | Description                                                                      |
| ------------- | ------------------ | -------------------------------------------------------------------------------- |
| `deploy.yml`  | Push to any branch | Builds and deploys all services                                                  |
| `cleanup.yml` | Manual             | Destroys an environment (Terraform, Redis keys, Temporal namespace, Neon branch) |

### First Deployment

1. Complete `pnpm run setup` wizard
2. Push to `main` — deployment runs automatically
3. After deployment, set `VITE_BACKEND_URL` variable with your backend URL
4. Push again to redeploy frontend with the backend URL

---

## Configuration

### GitHub Secrets

Set these in **Settings → Secrets and variables → Actions → Secrets**:

| Secret                | Required  | Description                                                             |
| --------------------- | --------- | ----------------------------------------------------------------------- |
| `GCP_PROJECT_ID`      | Yes       | Google Cloud project ID                                                 |
| `GOOGLE_CREDENTIALS`  | Yes       | Service account JSON key                                                |
| `TFSTATE_BUCKET`      | Yes       | GCS bucket for Terraform state                                          |
| `DATABASE_URL`        | Prod only | Neon PostgreSQL connection string (non-prod gets auto-created branches) |
| `NEON_API_KEY`        | Yes       | Neon API key for branch management                                      |
| `NEON_PROJECT_ID`     | Yes       | Neon project ID                                                         |
| `CLERK_SECRET_KEY`    | Yes       | Clerk backend API key                                                   |
| `OPENAI_API_KEY`      | Optional  | OpenAI API key                                                          |
| `ANTHROPIC_API_KEY`   | Optional  | Anthropic API key                                                       |
| `GEMINI_API_KEY`      | Optional  | Google Gemini API key                                                   |
| `LANGFUSE_PUBLIC_KEY` | Optional  | Langfuse public key (LLM observability)                                 |
| `LANGFUSE_SECRET_KEY` | Optional  | Langfuse secret key                                                     |
| `TEMPORAL_API_KEY`    | Optional  | Temporal Cloud API key (enables Temporal)                               |

**Note**: At least one LLM provider API key is required (OpenAI, Anthropic, or Gemini).

### Google Secret Manager

Redis URLs are stored in Google Secret Manager (not GitHub Secrets):

| Secret              | Description                              |
| ------------------- | ---------------------------------------- |
| `redis-url-prod`    | Redis Cloud URL for production           |
| `redis-url-staging` | Redis Cloud URL for staging              |
| `redis-url-dev`     | Redis Cloud URL for dev/feature branches |

### GitHub Variables

Set these in **Settings → Secrets and variables → Actions → Variables**:

| Variable                     | Default           | Description                            |
| ---------------------------- | ----------------- | -------------------------------------- |
| `APP_NAME`                   | (from repo)       | App name for GCP resources             |
| `REGION`                     | `asia-southeast1` | GCP region                             |
| `VITE_BACKEND_URL`           | -                 | Backend URL (set after first deploy)   |
| `VITE_CLERK_PUBLISHABLE_KEY` | -                 | Clerk frontend key                     |
| `CORS_ORIGINS`               | `*`               | Allowed CORS origins (comma-separated) |

### Service Account Setup

The GCP service account needs these IAM roles:

- Artifact Registry Administrator
- Cloud Run Admin
- Service Account User
- Storage Admin
- Secret Manager Admin

For Tomoro team: Contact Ross Comrie or Rishabh Sagar for permissions.

---

## Architecture

### Services

```
┌─────────────────────────────────────────────────────────────────┐
│                         Cloud Run                                │
├─────────────────┬─────────────────┬─────────────────────────────┤
│    Frontend     │     Backend     │           Worker            │
│   (React SPA)   │    (FastAPI)    │    (Redis/Temporal)         │
└────────┬────────┴────────┬────────┴────────┬────────────────────┘
         │                 │                 │
         │                 ▼                 ▼
         │        ┌───────────────────────────────┐
         │        │      Shared Packages          │
         │        │  db, redis, storage, llm...   │
         │        └───────────────────────────────┘
         │                 │
         ▼                 ▼
┌─────────────┐  ┌─────────────────┐  ┌─────────────┐  ┌──────┐
│    Clerk    │  │      Neon       │  │ Redis Cloud │  │ GCS  │
│   (Auth)    │  │  (PostgreSQL)   │  │  (shared)   │  │      │
└─────────────┘  └─────────────────┘  └─────────────┘  └──────┘
```

### Background Jobs

**Redis Streams** (Redis Cloud):

- Simple job queue for background processing
- Progress tracking via Redis pub/sub
- SSE streaming to frontend
- App isolation via key prefixing on shared Redis Cloud instances

**Temporal Workflows** (optional):

- Durable, long-running workflows
- Automatic retries with configurable policies
- Full visibility in Temporal UI
- Enable by setting `TEMPORAL_API_KEY`

---

## Shared Packages

All services share code via `packages/`:

| Package               | Description                                     |
| --------------------- | ----------------------------------------------- |
| `packages/db`         | SQLAlchemy models, migrations, database session |
| `packages/redis`      | Redis client, pub/sub, job queues               |
| `packages/storage`    | GCS storage with presigned URLs                 |
| `packages/openai`     | OpenAI wrapper with retry logic                 |
| `packages/anthropic`  | Anthropic wrapper with retry logic              |
| `packages/gemini`     | Gemini wrapper with retry logic                 |
| `packages/llm`        | Shared LLM types (prevents drift)               |
| `packages/temporal`   | Temporal workflows and activities               |
| `packages/langfuse`   | LLM observability decorators                    |
| `packages/logging`    | Colored logging for development                 |
| `packages/exceptions` | Domain exceptions with HTTP mapping             |

### Usage Example

```python
# Database
from packages.db import User, File, get_db

# LLM providers
import packages.openai as openai
import packages.anthropic as anthropic

response = await openai.chat([{"role": "user", "content": "Hello"}])
async for chunk in anthropic.stream_chat(messages, model="sonnet"):
    print(chunk, end="")

# Background jobs
from packages.redis.queue import JobQueue
queue = JobQueue(redis)
await queue.enqueue("process_file", {"file_id": "..."})
```

---

## Troubleshooting

<details>
<summary><strong>Port already in use</strong></summary>

```bash
pnpm down
pnpm clean
pnpm dev
```

</details>

<details>
<summary><strong>Database migration issues</strong></summary>

```bash
pnpm db:rollback
pnpm db:migrate

# Or reset completely
pnpm db:reset
```

</details>

<details>
<summary><strong>Frontend can't connect to backend</strong></summary>

1. Get backend URL from deployment logs
2. Set `VITE_BACKEND_URL` in GitHub Variables
3. Redeploy frontend
</details>

<details>
<summary><strong>Temporal workflows not working</strong></summary>

1. Check `TEMPORAL_API_KEY` is set in GitHub Secrets
2. Verify worker is running: `pnpm worker:logs`
3. Check Temporal UI: `pnpm temporal:ui`
</details>

<details>
<summary><strong>Redis connection issues</strong></summary>

1. Verify Redis URL is set in Google Secret Manager (`redis-url-prod`, `redis-url-staging`, `redis-url-dev`)
2. Local: `pnpm redis:cli` to test connection
3. Check key prefix in `features.json` → `app.id`
</details>

---

## Documentation

- **[CLAUDE.md](./CLAUDE.md)** - AI assistant documentation with patterns and conventions
- **[Notion Docs](https://www.notion.so/Full-Stack-Template-26f0de3387ea809ab1feeccd752c9a17)** - Comprehensive guide

---

## License

MIT License - see [LICENSE](LICENSE)

---

<div align="center">
  <strong>Happy coding!</strong>
  <br>
  <sub>Built with love by Tomoro AI</sub>
</div>
