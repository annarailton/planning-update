# Implementation Plan: Feature Flags, Lean Containers & CI/CD Simplification

## Overview

This plan addresses three related goals:

1. **Lean container images** - Only include dependencies for enabled features (~200MB vs ~400MB)
2. **Feature flag system** - Single `features.json` controls everything
3. **CI/CD simplification** - 14 workflows → 4

## Architecture

```
features.json (source of truth)
     │
     ├──► Docker build args ──► Conditional pip install ──► Lean images
     │
     ├──► CI/CD workflows ──► Conditional build/deploy jobs
     │
     ├──► Terraform vars ──► Conditional resource creation
     │
     ├──► Docker Compose profiles ──► Conditional local services
     │
     └──► Runtime config ──► Conditional route registration
```

---

## Phase 1: Optional Dependencies Foundation

### 1.1 Update Backend `pyproject.toml`

Move feature-specific dependencies to optional groups:

```toml
[project]
name = "backend"
version = "0.1.0"
requires-python = ">=3.12"

# Core dependencies only - always installed
dependencies = [
    # FastAPI core
    "fastapi[standard]>=0.115.11",
    "uvicorn[standard]>=0.34.0",
    "httpx>=0.28.1",
    "pydantic>=2.10.6",
    "pydantic-settings>=2.7.0",
    "python-dotenv>=1.0.1",
    # Database
    "sqlalchemy>=2.0.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "psycopg2-binary>=2.9.10",
    # Authentication
    "clerk-backend-api>=3.0.3",
    "pyjwt[crypto]>=2.10.1",
    # Utilities
    "pyhumps>=3.8.0",
    "pyyaml>=6.0.2",
    "google-cloud-storage>=3.3.0",
]

[project.optional-dependencies]
# Feature: Redis (jobs, queues, pub/sub)
redis = ["redis>=7.1.0"]

# Feature: Temporal (durable workflows)
temporal = ["temporalio>=1.9.0"]

# Feature: LLM Providers
llm-openai = ["openai>=2.14.0", "openai-agents[sqlalchemy]>=0.4.2"]
llm-anthropic = ["anthropic>=0.75.0"]
llm-gemini = ["google-genai>=1.56.0"]

# Feature: LLM Observability
langfuse = ["langfuse>=3.0.0"]

# All features (for development)
all = [
    "backend[redis,temporal,llm-openai,llm-anthropic,llm-gemini,langfuse]"
]
```

### 1.2 Update Backend Dockerfile

Accept feature flags as build args and install conditionally:

```dockerfile
# Production Dockerfile for Backend
FROM python:3.12-slim AS builder

# Feature flags from features.json (passed via --build-arg)
ARG FEATURE_REDIS=false
ARG FEATURE_TEMPORAL=false
ARG FEATURE_LLM_OPENAI=true
ARG FEATURE_LLM_ANTHROPIC=false
ARG FEATURE_LLM_GEMINI=false
ARG FEATURE_LANGFUSE=false

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy shared packages
COPY packages/ /packages/

# Copy application code
COPY services/backend/app/ ./

# Build extras string based on features
RUN EXTRAS="" && \
    [ "$FEATURE_REDIS" = "true" ] && EXTRAS="${EXTRAS:+$EXTRAS,}redis" || true && \
    [ "$FEATURE_TEMPORAL" = "true" ] && EXTRAS="${EXTRAS:+$EXTRAS,}temporal" || true && \
    [ "$FEATURE_LLM_OPENAI" = "true" ] && EXTRAS="${EXTRAS:+$EXTRAS,}llm-openai" || true && \
    [ "$FEATURE_LLM_ANTHROPIC" = "true" ] && EXTRAS="${EXTRAS:+$EXTRAS,}llm-anthropic" || true && \
    [ "$FEATURE_LLM_GEMINI" = "true" ] && EXTRAS="${EXTRAS:+$EXTRAS,}llm-gemini" || true && \
    [ "$FEATURE_LANGFUSE" = "true" ] && EXTRAS="${EXTRAS:+$EXTRAS,}langfuse" || true && \
    echo "Installing with extras: $EXTRAS" && \
    if [ -n "$EXTRAS" ]; then \
        uv sync --frozen --no-dev --extra "$EXTRAS"; \
    else \
        uv sync --frozen --no-dev; \
    fi

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Copy only what we need from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /packages /packages
COPY --from=builder /app /app

# Copy entrypoint
COPY services/backend/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

ENV PYTHONPATH=/
ENV UV_NO_SYNC=1

EXPOSE 8080

ENTRYPOINT ["docker-entrypoint.sh"]
CMD [".venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 1.3 Update Worker `pyproject.toml`

Similar pattern - worker always needs redis, optionally temporal:

```toml
[project]
name = "worker"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    # Core worker deps
    "redis>=7.1.0",  # Worker always needs redis
    "httpx>=0.28.1",
    "pydantic>=2.10.6",
    "pydantic-settings>=2.7.0",
]

[project.optional-dependencies]
temporal = ["temporalio>=1.9.0"]
gpu = []  # GPU client uses httpx (already in core)
all = ["worker[temporal]"]
```

### 1.4 Guarded Imports in Code

Update imports to handle missing packages gracefully:

```python
# services/backend/app/main.py
def create_app() -> FastAPI:
    settings = get_settings()

    # ... core setup ...

    # Conditional: Redis/Jobs
    if settings.is_redis_enabled:
        try:
            from routers import jobs
            api_router.include_router(jobs.router)
            logger.info("Redis routes enabled")
        except ImportError:
            logger.warning("Redis feature enabled but package not installed")

    # Conditional: Temporal/Workflows
    if settings.is_temporal_enabled:
        try:
            from routers import workflows
            api_router.include_router(workflows.router)
            logger.info("Temporal routes enabled")
        except ImportError:
            logger.warning("Temporal feature enabled but package not installed")
```

---

## Phase 2: Feature Flag System

### 2.1 Create `features.json`

```json
{
  "redis": false,
  "temporal": false,
  "gpu": false,
  "langfuse": false,
  "llm": {
    "openai": true,
    "anthropic": false,
    "gemini": false
  }
}
```

### 2.2 Create `scripts/features.sh`

Parses features.json for use by:

- Docker build (--build-arg)
- CI/CD (GitHub Actions outputs)
- Docker Compose (--profile flags)
- Shell scripts (environment variables)

```bash
#!/bin/bash
# Usage:
#   ./scripts/features.sh --docker-args  # For docker build
#   ./scripts/features.sh --github       # For CI/CD outputs
#   ./scripts/features.sh --profiles     # For docker compose
#   source scripts/features.sh           # Export to shell
```

### 2.3 Backend Config Updates

```python
# services/backend/app/core/config.py
class Settings(BaseSettings):
    # Feature flags (from env vars, set by CI/CD from features.json)
    feature_redis: bool = Field(default=False)
    feature_temporal: bool = Field(default=False)
    feature_gpu: bool = Field(default=False)
    feature_langfuse: bool = Field(default=False)
    feature_llm_openai: bool = Field(default=True)
    feature_llm_anthropic: bool = Field(default=False)
    feature_llm_gemini: bool = Field(default=False)

    @property
    def is_redis_enabled(self) -> bool:
        """Redis enabled AND configured."""
        return self.feature_redis and bool(self.redis_url)

    @property
    def is_temporal_enabled(self) -> bool:
        """Temporal enabled AND configured."""
        return self.feature_temporal and (
            bool(self.temporal_address) or bool(self.temporal_api_key)
        )
```

### 2.4 Features API Endpoint

```python
# services/backend/app/routers/features.py
@router.get("/features")
async def get_features() -> dict:
    """Return enabled features for frontend consumption."""
    settings = get_settings()
    return {
        "redis": settings.is_redis_enabled,
        "temporal": settings.is_temporal_enabled,
        "gpu": settings.is_gpu_enabled,
        "llm": {
            "openai": settings.feature_llm_openai and bool(settings.openai_api_key),
            "anthropic": settings.feature_llm_anthropic and bool(settings.anthropic_api_key),
            "gemini": settings.feature_llm_gemini and bool(settings.gemini_api_key),
        },
    }
```

---

## Phase 3: Frontend Reverse Proxy

### 3.1 Update `nginx.conf`

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Proxy API requests to backend
    location /api/ {
        proxy_pass ${BACKEND_URL};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE/WebSocket support
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        proxy_set_header Connection '';
        chunked_transfer_encoding off;
    }

    # Serve static files
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
}
```

### 3.2 Create `docker-entrypoint.sh`

```bash
#!/bin/sh
# Substitute environment variables in nginx config
envsubst '${BACKEND_URL}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
```

### 3.3 Update Frontend Dockerfile

```dockerfile
FROM node:18-alpine AS builder
# ... build stage unchanged ...

FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config as template
COPY services/frontend/nginx.conf /etc/nginx/templates/default.conf.template

# Copy entrypoint
COPY services/frontend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
```

### 3.4 Frontend `useFeatures` Hook

```typescript
// services/frontend/app/src/shared/hooks/useFeatures.ts
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/shared/lib/api-client";

interface Features {
  redis: boolean;
  temporal: boolean;
  gpu: boolean;
  llm: {
    openai: boolean;
    anthropic: boolean;
    gemini: boolean;
  };
}

export function useFeatures() {
  return useQuery({
    queryKey: ["features"],
    queryFn: async () => {
      const response = await apiClient.get<Features>("/api/features");
      return response.data;
    },
    staleTime: Infinity, // Features don't change at runtime
  });
}
```

---

## Phase 4: Docker Compose Profiles

### 4.1 Update `docker-compose.yml`

```yaml
services:
  backend:
    # Always runs (no profile)
    build:
      context: .
      dockerfile: ./services/backend/Dockerfile.dev

  frontend:
    # Always runs (no profile)
    build:
      context: .
      dockerfile: ./services/frontend/Dockerfile.dev

  redis:
    profiles: ["redis", "temporal"] # temporal requires redis
    image: redis:8.4-alpine

  redis-insight:
    profiles: ["redis", "temporal"]
    image: redis/redisinsight:latest

  worker:
    profiles: ["redis"]
    build:
      context: .
      dockerfile: ./services/worker/Dockerfile.dev

  temporal-db:
    profiles: ["temporal"]
    image: postgres:16-alpine

  temporal:
    profiles: ["temporal"]
    image: temporalio/auto-setup:latest

  temporal-ui:
    profiles: ["temporal"]
    image: temporalio/ui:latest

  gpu-worker:
    profiles: ["gpu"]
    build:
      context: .
      dockerfile: ./services/gpu-worker/Dockerfile.dev
```

### 4.2 Create `scripts/dev.sh`

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FEATURES_FILE="$PROJECT_ROOT/features.json"

# Build profile flags from features.json
PROFILES=$(python3 << EOF
import json
with open("$FEATURES_FILE") as f:
    features = json.load(f)

profiles = []
if features.get("redis", False):
    profiles.append("--profile redis")
if features.get("temporal", False):
    profiles.append("--profile temporal")
if features.get("gpu", False):
    profiles.append("--profile gpu")

print(" ".join(profiles))
EOF
)

echo "Starting with profiles: $PROFILES"
docker compose $PROFILES up "$@"
```

### 4.3 Update `package.json`

```json
{
  "scripts": {
    "dev": "./scripts/dev.sh",
    "dev:all": "docker compose --profile redis --profile temporal --profile gpu up",
    "dev:build": "./scripts/dev.sh --build"
  }
}
```

---

## Phase 5: CI/CD Simplification (14 → 4 workflows)

### 5.1 `validation.yml` - PR Checks

```yaml
name: Validate

on:
  pull_request:
    branches: [main, staging]

jobs:
  lint-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: cd services/backend/app && uv sync --frozen
      - run: cd services/backend/app && uv run ruff check .
      - run: cd services/backend/app && uv run black --check .

  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: cd services/backend/app && uv sync --frozen --all-extras
      - run: cd services/backend/app && uv run pytest

  lint-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - run: cd services/frontend/app && pnpm install
      - run: cd services/frontend/app && pnpm lint
      - run: cd services/frontend/app && pnpm typecheck

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - run: cd services/frontend/app && pnpm install
      - run: cd services/frontend/app && pnpm test:run

  verify-builds:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Load features
        id: features
        run: ./scripts/features.sh --github >> $GITHUB_OUTPUT
      - name: Build backend
        run: |
          docker build \
            --build-arg FEATURE_REDIS=${{ steps.features.outputs.redis }} \
            --build-arg FEATURE_TEMPORAL=${{ steps.features.outputs.temporal }} \
            -f services/backend/Dockerfile .
      - name: Build frontend
        run: docker build -f services/frontend/Dockerfile .
      - name: Build worker
        if: steps.features.outputs.redis == 'true'
        run: docker build -f services/worker/Dockerfile .
```

### 5.2 `deploy.yml` - Manual Deployment

```yaml
name: Deploy

on:
  workflow_dispatch:
    inputs:
      environment:
        description: "Environment (auto = branch name)"
        default: "auto"
        type: choice
        options: [auto, dev, staging, prod]

jobs:
  config:
    runs-on: ubuntu-latest
    outputs:
      environment: ${{ steps.env.outputs.environment }}
      redis: ${{ steps.features.outputs.redis }}
      temporal: ${{ steps.features.outputs.temporal }}
      gpu: ${{ steps.features.outputs.gpu }}
    steps:
      - uses: actions/checkout@v4
      - name: Determine environment
        id: env
        run: |
          if [ "${{ inputs.environment }}" = "auto" ]; then
            echo "environment=${{ github.ref_name }}" >> $GITHUB_OUTPUT
          else
            echo "environment=${{ inputs.environment }}" >> $GITHUB_OUTPUT
          fi
      - name: Load features
        id: features
        run: ./scripts/features.sh --github >> $GITHUB_OUTPUT

  database:
    needs: config
    if: needs.config.outputs.environment != 'prod' && needs.config.outputs.environment != 'staging'
    uses: ./.github/workflows/_neon.yml
    with:
      action: create
      branch_name: ${{ needs.config.outputs.environment }}
    secrets: inherit

  build-backend:
    needs: config
    runs-on: ubuntu-latest
    outputs:
      image_url: ${{ steps.build.outputs.image_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - name: Build and push
        id: build
        run: |
          # Build with feature flags
          docker build \
            --build-arg FEATURE_REDIS=${{ needs.config.outputs.redis }} \
            --build-arg FEATURE_TEMPORAL=${{ needs.config.outputs.temporal }} \
            --build-arg FEATURE_LLM_OPENAI=true \
            -t $IMAGE_URL \
            -f services/backend/Dockerfile .
          docker push $IMAGE_URL
          echo "image_url=$IMAGE_URL" >> $GITHUB_OUTPUT

  build-worker:
    needs: config
    if: needs.config.outputs.redis == 'true'
    runs-on: ubuntu-latest
    outputs:
      image_url: ${{ steps.build.outputs.image_url }}
    # ... similar to build-backend

  build-frontend:
    needs: config
    runs-on: ubuntu-latest
    outputs:
      image_url: ${{ steps.build.outputs.image_url }}
    # ... build frontend

  deploy-backend:
    needs: [config, database, build-backend]
    if: always() && needs.build-backend.result == 'success'
    runs-on: ubuntu-latest
    outputs:
      backend_url: ${{ steps.deploy.outputs.backend_url }}
      redis_url: ${{ steps.deploy.outputs.redis_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - name: Deploy
        id: deploy
        working-directory: terraform/services/backend
        env:
          TF_VAR_feature_redis: ${{ needs.config.outputs.redis }}
          TF_VAR_feature_temporal: ${{ needs.config.outputs.temporal }}
          TF_VAR_image_url: ${{ needs.build-backend.outputs.image_url }}
          TF_VAR_database_url: ${{ needs.database.outputs.database_url || secrets.DATABASE_URL }}
        run: |
          terraform init -backend-config="bucket=${{ secrets.TF_STATE_BUCKET }}"
          terraform workspace select -or-create ${{ needs.config.outputs.environment }}
          terraform apply -auto-approve
          echo "backend_url=$(terraform output -raw service_url)" >> $GITHUB_OUTPUT

  deploy-worker:
    needs: [config, build-worker, deploy-backend]
    if: needs.config.outputs.redis == 'true' && needs.build-worker.result == 'success'
    # ... deploy worker with redis_url from backend

  deploy-frontend:
    needs: [config, build-frontend, deploy-backend]
    runs-on: ubuntu-latest
    steps:
      - uses: hashicorp/setup-terraform@v3
      - name: Deploy
        working-directory: terraform/services/frontend
        env:
          TF_VAR_image_url: ${{ needs.build-frontend.outputs.image_url }}
          TF_VAR_backend_url: ${{ needs.deploy-backend.outputs.backend_url }}
        run: |
          terraform init
          terraform workspace select -or-create ${{ needs.config.outputs.environment }}
          terraform apply -auto-approve

  summary:
    needs: [deploy-backend, deploy-frontend, deploy-worker]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Print URLs
        run: |
          echo "## Deployment Complete" >> $GITHUB_STEP_SUMMARY
          echo "| Service | URL |" >> $GITHUB_STEP_SUMMARY
          echo "|---------|-----|" >> $GITHUB_STEP_SUMMARY
          echo "| Frontend | ${{ needs.deploy-frontend.outputs.frontend_url }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Backend | ${{ needs.deploy-backend.outputs.backend_url }} |" >> $GITHUB_STEP_SUMMARY
```

### 5.3 `cleanup.yml` - Environment Cleanup

```yaml
name: Cleanup

on:
  workflow_dispatch:
    inputs:
      environment:
        description: "Environment to destroy"
        required: true
      confirm:
        description: "Type environment name to confirm"
        required: true

jobs:
  destroy:
    runs-on: ubuntu-latest
    if: inputs.environment == inputs.confirm
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3

      - name: Destroy frontend
        working-directory: terraform/services/frontend
        run: |
          terraform init
          terraform workspace select ${{ inputs.environment }}
          terraform destroy -auto-approve
          terraform workspace select default
          terraform workspace delete ${{ inputs.environment }}

      - name: Destroy worker
        working-directory: terraform/services/worker
        continue-on-error: true # May not exist
        run: |
          terraform init
          terraform workspace select ${{ inputs.environment }}
          terraform destroy -auto-approve

      - name: Destroy backend
        working-directory: terraform/services/backend
        run: |
          terraform init
          terraform workspace select ${{ inputs.environment }}
          terraform destroy -auto-approve

      - name: Delete Neon branch
        uses: ./.github/workflows/_neon.yml
        with:
          action: delete
          branch_name: ${{ inputs.environment }}
```

### 5.4 `production.yml` - Auto-deploy Main/Staging

```yaml
name: Production

on:
  push:
    branches: [main, staging]

jobs:
  deploy:
    uses: ./.github/workflows/deploy.yml
    with:
      environment: ${{ github.ref_name == 'main' && 'prod' || 'staging' }}
    secrets: inherit
```

### 5.5 Delete Old Workflows

After testing, delete:

- `_backend.yml`, `_frontend.yml`, `_worker.yml`, `_gpu-worker.yml`
- `backend-deploy.yml`, `frontend-deploy.yml`, `worker-deploy.yml`, `gpu-worker-deploy.yml`
- `deploy-all.yml`, `destroy-services.yml`, `database-destroy.yml`

Keep: `_neon.yml` (reused by deploy/cleanup)

---

## Phase 6: Terraform Feature Integration

### 6.1 Add Feature Variables

```hcl
# terraform/services/backend/variables.tf
variable "feature_redis" {
  description = "Enable Redis features"
  type        = bool
  default     = false
}

variable "feature_temporal" {
  description = "Enable Temporal workflows"
  type        = bool
  default     = false
}

variable "feature_gpu" {
  description = "Enable GPU worker"
  type        = bool
  default     = false
}
```

### 6.2 Conditional Resources

```hcl
# terraform/services/backend/main.tf

# Redis - only create if feature enabled
resource "rediscloud_subscription_database" "main" {
  count = var.feature_redis && var.redis_subscription_id != "" ? 1 : 0
  # ...
}

# Temporal - only create if feature enabled
resource "temporalcloud_namespace" "main" {
  count = var.feature_temporal && var.temporal_api_key != "" ? 1 : 0
  # ...
}

# Pass feature flags to Cloud Run
module "cloud_run" {
  env_vars = merge(
    { /* core vars */ },
    { FEATURE_REDIS = tostring(var.feature_redis) },
    { FEATURE_TEMPORAL = tostring(var.feature_temporal) },
    { FEATURE_GPU = tostring(var.feature_gpu) },
    # Only include URLs if feature enabled
    var.feature_redis && length(rediscloud_subscription_database.main) > 0 ? {
      REDIS_URL = "redis://..."
    } : {},
  )
}
```

### 6.3 Frontend Terraform Updates

```hcl
# terraform/services/frontend/variables.tf
variable "backend_url" {
  description = "Backend service URL for reverse proxy"
  type        = string
}

# terraform/services/frontend/main.tf
module "cloud_run" {
  env_vars = {
    NODE_ENV    = var.node_env
    BACKEND_URL = var.backend_url  # For nginx proxy
  }
}
```

---

## Files Summary

### Create

| File                                                    | Purpose                             |
| ------------------------------------------------------- | ----------------------------------- |
| `features.json`                                         | Feature flag source of truth        |
| `scripts/features.sh`                                   | Parse features for various contexts |
| `scripts/dev.sh`                                        | Start dev with correct profiles     |
| `services/backend/app/routers/features.py`              | `/api/features` endpoint            |
| `services/frontend/docker-entrypoint.sh`                | nginx env substitution              |
| `services/frontend/app/src/shared/hooks/useFeatures.ts` | Frontend feature hook               |
| `.github/workflows/validation.yml`                      | PR validation                       |
| `.github/workflows/deploy.yml`                          | Manual deployment                   |
| `.github/workflows/cleanup.yml`                         | Environment cleanup                 |
| `.github/workflows/production.yml`                      | Auto-deploy main/staging            |

### Modify

| File                                       | Changes                             |
| ------------------------------------------ | ----------------------------------- |
| `services/backend/app/pyproject.toml`      | Optional dependency groups          |
| `services/backend/Dockerfile`              | Build args for features             |
| `services/backend/app/core/config.py`      | Feature flag settings               |
| `services/backend/app/main.py`             | Guarded imports, conditional routes |
| `services/worker/app/pyproject.toml`       | Optional dependency groups          |
| `services/worker/Dockerfile`               | Build args for features             |
| `services/frontend/nginx.conf`             | Add /api proxy                      |
| `services/frontend/Dockerfile`             | Use entrypoint for env              |
| `terraform/services/backend/variables.tf`  | Feature variables                   |
| `terraform/services/backend/main.tf`       | Conditional resources               |
| `terraform/services/frontend/variables.tf` | Add backend_url                     |
| `terraform/services/frontend/main.tf`      | Pass backend_url                    |
| `docker-compose.yml`                       | Add profiles                        |
| `package.json`                             | Update dev script                   |

### Delete (after testing)

- `.github/workflows/_backend.yml`
- `.github/workflows/_frontend.yml`
- `.github/workflows/_worker.yml`
- `.github/workflows/_gpu-worker.yml`
- `.github/workflows/backend-deploy.yml`
- `.github/workflows/frontend-deploy.yml`
- `.github/workflows/worker-deploy.yml`
- `.github/workflows/gpu-worker-deploy.yml`
- `.github/workflows/deploy-all.yml`
- `.github/workflows/destroy-services.yml`
- `.github/workflows/database-destroy.yml`

---

## Implementation Order

1. **Phase 1.1-1.4**: Optional dependencies + guarded imports
2. **Phase 2**: Feature flag system (features.json, config, /api/features)
3. **Phase 5**: Docker Compose profiles + dev.sh (enables local testing)
4. **Phase 3**: Frontend reverse proxy
5. **Phase 6**: Terraform feature integration
6. **Phase 4**: New CI/CD workflows
7. **Cleanup**: Delete old workflows after testing

---

## Verification Checklist

### Local Dev

- [ ] `pnpm dev` starts only backend + frontend (redis/temporal disabled)
- [ ] Edit `features.json` to `redis: true`, restart, worker starts
- [ ] Backend `/api/features` returns correct enabled features
- [ ] Frontend useFeatures hook receives features

### Container Size

- [ ] Backend image with all features disabled: ~200MB
- [ ] Backend image with all features enabled: ~400MB
- [ ] Worker image: ~150MB

### CI/CD

- [ ] PR triggers validation.yml (~3-5 min)
- [ ] Manual deploy.yml creates environment via Terraform
- [ ] Manual cleanup.yml destroys all resources
- [ ] Push to main triggers production.yml

### Reverse Proxy

- [ ] Frontend `/api/*` proxies to backend
- [ ] SSE streaming works through proxy
- [ ] Backend docs at `/api/docs` accessible
