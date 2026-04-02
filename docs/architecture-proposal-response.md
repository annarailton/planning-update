# Architecture Proposal Response

## Executive Summary

After thorough analysis of the proposed refactoring, we agree with the core goals: simplify CI/CD, reduce operational complexity, and improve developer experience. However, we disagree with bundling frontend and backend into a single service.

This document proposes an alternative approach that achieves the same goals while preserving architectural flexibility:

1. **Reverse proxy pattern** - Single domain without bundling
2. **On-demand preview environments** - Developer-triggered, not automatic
3. **Foundation vs runtime split** - Terraform once, gcloud for deployments
4. **Minimal workflows** - 4 files instead of 14

---

## What We Agree With

### 1. The Template Does Too Many Jobs (Correct Diagnosis)

The CTO correctly identifies that the template currently handles:

1. **Scaffolding a product codebase** - good fit for a template
2. **Implementing shared libraries/patterns** - good fit for a template
3. **Platform/infrastructure distribution** - painful to maintain as a template

This is a valid concern. Every new app becomes a fork of the platform, making evolution difficult.

### 2. CI/CD Is Over-Engineered (Proposals 4, 5, 6)

**Current state**: 14 workflow files, 2,060 lines of YAML, automatic PR previews with full Terraform runs.

**Problems**:

- Every PR triggers 4 Terraform applies (15-20 min)
- State contention with concurrent PRs
- Most PRs don't need cloud preview environments
- Complex orchestration between workflows

**We agree**: This should be dramatically simplified.

### 3. Bootstrap vs Dev Split (Proposal 7)

**We agree**: Clear separation between one-time setup and daily workflows improves DX.

---

## What We Disagree With

### 1. Bundling Frontend + Backend into Single Service (Proposals 1 & 2)

**This is the core disagreement.** While the simplicity argument is appealing, it creates operational problems at scale.

#### Technical Issues

| Concern                 | Separate Services                                 | Bundled Service                                                              |
| ----------------------- | ------------------------------------------------- | ---------------------------------------------------------------------------- |
| **Scaling**             | Each service scales based on its own requirements | Forced to scale based on whichever is the bottleneck                         |
| **Container size**      | Small, focused containers                         | Bloated container = slower cold starts, slower deploys, more memory overhead |
| **Deployments**         | Independent rollbacks, parallel builds            | Full rebuild for any change                                                  |
| **Resource efficiency** | Right tool for each job                           | Paying for Python runtime overhead to serve static files                     |

#### The Multi-Frontend Future

The `services/` directory structure anticipates growth:

```
services/
  frontend/        # React web app
  backend/         # FastAPI API (serves all clients)
  worker/          # Background jobs
  admin/           # (future) Admin dashboard
```

If we bundle frontend into backend:

- Adding admin dashboard requires unbundling or awkward multi-SPA setup
- Mobile apps would hit the same bundle that serves web static files they don't need
- We've optimized for a single-frontend world that won't last

#### Better Alternative: Reverse Proxy Pattern

If the concern is CORS and single-domain UX, we achieve that **without bundling**:

```
User Request
     │
     ▼
┌─────────────────────────────────────┐
│  Frontend Cloud Run (Nginx)         │
│  app.example.com                    │
│                                     │
│  /api/*  ──► proxy to Backend       │
│  /*      ──► serve static files     │
└─────────────────────────────────────┘
           │
           ▼ (internal traffic)
┌─────────────────────────────────────┐
│  Backend Cloud Run (FastAPI)        │
│  ingress: internal-only             │
└─────────────────────────────────────┘
```

**Benefits**:

- Single domain (no CORS)
- Services remain separate (proper scaling)
- Backend can be internal-only (more secure)
- Swagger still accessible at `/api/docs`

### 2. Automatic PR Preview Environments (Proposal 3)

**We reject automatic PR previews entirely.**

Current approach deploys full environments on every PR. This is wasteful:

- Most PRs are small changes that don't need cloud testing
- Developers can test locally with `pnpm dev`
- Automatic provisioning is slow and expensive
- Creates cleanup burden

**Better alternative**: On-demand preview environments (see proposal below).

---

## Our Proposal

### Architecture: Reverse Proxy for Production

Single domain without bundling services.

**Frontend Nginx** (`services/frontend/nginx.conf`):

```nginx
server {
    listen 80;
    resolver 8.8.8.8 valid=10s;
    set $backend "${BACKEND_URL}";

    # Proxy API requests to backend
    location /api/ {
        proxy_pass $backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Serve static files
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # ... existing caching and security headers
}
```

**Backend** (`services/backend/app/main.py`):

```python
# Move Swagger under /api for clean proxying
app = FastAPI(
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
```

**Frontend Dockerfile** - use Nginx's built-in envsubst:

```dockerfile
# Nginx auto-runs envsubst on .template files
COPY services/frontend/nginx.conf /etc/nginx/templates/default.conf.template
```

### CI/CD: Minimal Workflows

Replace 14 workflow files with 4:

```
.github/workflows/
  validation.yml     # Automatic on PR: lint, test, build check
  deploy.yml         # Manual trigger: deploy any branch
  cleanup.yml        # Manual trigger: destroy environment
  production.yml     # Automatic on main/staging: production deploy
```

#### validation.yml (Automatic)

Runs on every PR - fast feedback, no deployment:

```yaml
name: Validate PR

on:
  pull_request:

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Backend checks
        run: |
          pnpm lint:backend
          pnpm test:backend

      - name: Frontend checks
        run: |
          pnpm lint:frontend
          pnpm test:frontend

      - name: Verify Docker builds
        run: |
          docker build -f services/backend/Dockerfile .
          docker build -f services/frontend/Dockerfile .
```

**Time**: ~3-5 minutes. No deployment, no Terraform.

#### deploy.yml (Manual - On Demand)

Developer triggers when they need cloud testing:

```yaml
name: Deploy Preview

on:
  workflow_dispatch:
    inputs:
      environment:
        description: "Environment name (defaults to branch name)"
        required: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    env:
      ENV_NAME: ${{ inputs.environment || github.ref_name }}

    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GOOGLE_CREDENTIALS }}

      - name: Build and push images
        run: |
          docker build -t gcr.io/$PROJECT/backend:$ENV_NAME -f services/backend/Dockerfile .
          docker build -t gcr.io/$PROJECT/frontend:$ENV_NAME -f services/frontend/Dockerfile .
          docker push gcr.io/$PROJECT/backend:$ENV_NAME
          docker push gcr.io/$PROJECT/frontend:$ENV_NAME

      - name: Create Neon branch
        run: |
          neon branches create --name $ENV_NAME || true
          DATABASE_URL=$(neon connection-string --branch $ENV_NAME)
          echo "DATABASE_URL=$DATABASE_URL" >> $GITHUB_ENV

      - name: Create Redis database
        run: |
          # Create Redis database for this branch
          # (implementation depends on Redis Cloud API or Terraform)

      - name: Create GCS bucket
        run: |
          gcloud storage buckets create gs://$PROJECT-$ENV_NAME --location=$REGION || true

      - name: Deploy backend
        run: |
          gcloud run deploy backend-$ENV_NAME \
            --image gcr.io/$PROJECT/backend:$ENV_NAME \
            --set-env-vars "DATABASE_URL=$DATABASE_URL" \
            --set-env-vars "REDIS_URL=$REDIS_URL" \
            --set-env-vars "GCS_BUCKET=$PROJECT-$ENV_NAME" \
            --region $REGION \
            --allow-unauthenticated

      - name: Deploy frontend
        run: |
          BACKEND_URL=$(gcloud run services describe backend-$ENV_NAME --format='value(status.url)')
          gcloud run deploy frontend-$ENV_NAME \
            --image gcr.io/$PROJECT/frontend:$ENV_NAME \
            --set-env-vars "BACKEND_URL=$BACKEND_URL" \
            --region $REGION \
            --allow-unauthenticated

      - name: Output URLs
        run: |
          echo "Frontend: $(gcloud run services describe frontend-$ENV_NAME --format='value(status.url)')"
          echo "Backend: $BACKEND_URL"
```

**Triggered by**:

- GitHub UI: Actions → Deploy Preview → Run workflow
- GitHub CLI: `gh workflow run deploy.yml -f environment=my-feature`
- Local alias: `pnpm deploy:preview`

#### cleanup.yml (Manual)

Developer cleans up when done:

```yaml
name: Cleanup Environment

on:
  workflow_dispatch:
    inputs:
      environment:
        description: "Environment to destroy"
        required: true

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - name: Delete Cloud Run services
        run: |
          gcloud run services delete backend-${{ inputs.environment }} --quiet || true
          gcloud run services delete frontend-${{ inputs.environment }} --quiet || true
          gcloud run services delete worker-${{ inputs.environment }} --quiet || true

      - name: Delete Neon branch
        run: neon branches delete ${{ inputs.environment }} || true

      - name: Delete Redis database
        run: |
          # Delete Redis database for this branch
          # (implementation depends on Redis Cloud API or Terraform)

      - name: Delete GCS bucket
        run: |
          gcloud storage rm -r gs://$PROJECT-${{ inputs.environment }} || true
```

#### production.yml (Automatic)

Deploys main/staging automatically:

```yaml
name: Production Deploy

on:
  push:
    branches: [main, staging]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ github.ref_name == 'main' && 'production' || 'staging' }}

    steps:
      - uses: actions/checkout@v4

      # For production, we use Terraform for auditability
      - name: Deploy via Terraform
        run: |
          cd terraform/services
          terraform init
          terraform workspace select ${{ github.ref_name == 'main' && 'prod' || 'staging' }}
          terraform apply -auto-approve
```

### Developer Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Developer works on feature branch                          │
│                                                             │
│  1. Local development: pnpm dev                             │
│  2. Push to branch                                          │
│  3. PR opened → validation.yml runs (lint, test, build)     │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            │                                   │
            ▼                                   ▼
┌───────────────────────┐          ┌───────────────────────────┐
│  Small change         │          │  Needs E2E cloud testing  │
│                       │          │                           │
│  • Review code        │          │  1. Trigger deploy.yml    │
│  • Approve & merge    │          │  2. Test on preview env   │
│  • Done               │          │  3. Review & approve      │
└───────────────────────┘          │  4. Merge                 │
                                   │  5. Trigger cleanup.yml   │
                                   └───────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Merge to main → production.yml auto-deploys                │
└─────────────────────────────────────────────────────────────┘
```

### Foundation Infrastructure (One-Time Setup)

Run manually when setting up new environment tiers:

```
terraform/
  foundation/           # Shared infrastructure
    main.tf             # Artifact Registry, GCS bucket, IAM
    variables.tf
  services/             # Service definitions (prod/staging only)
    backend/
    frontend/
    worker/
```

**Foundation creates** (run once):

- Artifact Registry repository
- IAM roles and service accounts
- Base networking/policies

**Preview environments create their own resources** (per branch):

- Neon database branch
- Redis database
- GCS bucket
- Cloud Run services

**Cleanup is developer responsibility** - trigger `cleanup.yml` when done to tear down all branch resources.

### Local Development

**pnpm setup** (one-time):

```bash
#!/bin/bash
# Copy environment files
cp environment/.env.backend.example environment/.env.backend
cp environment/.env.frontend.example environment/.env.frontend

# Verify Docker
docker info > /dev/null 2>&1 || { echo "Docker not running"; exit 1; }

# Pull images
docker compose pull

# Initial setup
docker compose up -d db redis
pnpm db:migrate

echo "Setup complete. Run 'pnpm dev' to start."
```

**pnpm dev** (daily):

```bash
docker compose up
```

---

## Implementation Phases

### Phase 1: Reverse Proxy + Workflow Consolidation (2-3 days)

1. **Update nginx.conf** with proxy configuration
2. **Update backend** to serve docs at `/api/docs`
3. **Update frontend Dockerfile** to use `.template` pattern
4. **Create 4 new workflows**: validation.yml, deploy.yml, cleanup.yml, production.yml
5. **Delete old workflows** after testing

### Phase 2: Foundation Terraform (1-2 days)

1. **Create `terraform/foundation/`** with shared resources
2. **Run foundation** for dev/staging/prod tiers
3. **Update deploy.yml** to use foundation outputs
4. **Simplify service Terraform** (prod/staging only)

### Phase 3: Developer Experience (Ongoing)

1. **Add `pnpm setup`** script
2. **Add `pnpm deploy:preview`** alias for `gh workflow run`
3. **Document new workflow** in README
4. **Add weekly stale environment cleanup** (optional)

---

## Future: Library Extraction

The CTO's vision of extracting packages is sound. Current structure is well-factored:

| Package                                  | Extraction Candidate | Notes                       |
| ---------------------------------------- | -------------------- | --------------------------- |
| `packages/db`                            | Yes                  | Generic SQLAlchemy patterns |
| `packages/redis`                         | Yes                  | Queue + pubsub abstractions |
| `packages/openai`, `anthropic`, `gemini` | Yes                  | LLM provider wrappers       |
| `packages/exceptions`                    | Yes                  | Domain exception patterns   |
| `packages/logging`                       | Yes                  | Structured logging          |

**Recommendation**: Extract when a second project needs them, not before.

---

## Decision Matrix

| Proposal                       | Decision     | Rationale                                             |
| ------------------------------ | ------------ | ----------------------------------------------------- |
| 1. Bundle frontend+backend     | **Rejected** | Reverse proxy achieves single domain without bundling |
| 2. Local split, deploy bundled | **Rejected** | Using reverse proxy instead                           |
| 3. One Cloud Run per PR        | **Modified** | On-demand previews instead of automatic               |
| 4. Reduce CI/CD surface        | **Adopted**  | 4 workflows instead of 14                             |
| 5. No TF in PRs                | **Adopted**  | Terraform everywhere, but on-demand                   |
| 6. Runtime-only PRs            | **Adopted**  | On-demand, not automatic                              |
| 7. Bootstrap vs dev split      | **Adopted**  | pnpm setup + pnpm dev                                 |

---

## Summary

**Decisions made:**

- **Reverse proxy** - Single domain without bundling (frontend proxies `/api/*` to backend)
- **On-demand preview environments** - Developer-triggered, not automatic
- **4 workflows instead of 14** - validation, deploy, cleanup, production
- **Terraform everywhere** - Same mechanism for dev and prod, different triggers
- **features.json** - Single source of truth for optional features (Redis, Temporal, GPU)
- **Per-branch isolation** - Neon, Redis, GCS with manual cleanup
- **`pnpm setup`** - One-time local configuration

**Architecture preserved:**

- Separate services (frontend, backend, worker) - scale independently
- Local development with Docker Compose
- Per-branch resource isolation for previews

**Benefits:**

- Faster PR validation (~3 min instead of ~20 min)
- Lower cost (no automatic preview environments)
- Simpler CI/CD (4 files instead of 14)
- Developer control over when to deploy previews
- Single domain (no CORS) via reverse proxy
- Optional features can be toggled without code changes

See `docs/TODO.md` for detailed implementation plan.
