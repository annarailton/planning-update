# Implementation TODO

See **[implementation-plan.md](./implementation-plan.md)** for the comprehensive plan.

## Quick Summary

**Goals:**

1. Lean container images (~200MB vs ~400MB) via optional dependencies
2. Feature flag system with `features.json` as single source of truth
3. CI/CD simplification (14 workflows → 4)
4. Frontend reverse proxy for single-domain architecture

## Completed

### Phase 1: Feature Flag Foundation

- [x] Create `features.json`
- [x] Create `scripts/features.sh`
- [x] Update `services/backend/app/pyproject.toml` with optional deps
- [x] Update `services/backend/Dockerfile` with build args
- [x] Update `services/worker/app/pyproject.toml` with optional deps
- [x] Update `services/worker/Dockerfile` with build args

### Phase 2: Backend Feature Flag Integration

- [x] Add feature\_\* settings to `core/config.py`
- [x] Add is\_\*\_enabled properties
- [x] Create `/api/features` endpoint
- [x] Update `main.py` with guarded imports and conditional router registration

### Phase 3: Frontend Reverse Proxy

- [x] Update `nginx.conf` with /api proxy
- [x] Create `docker-entrypoint.sh` for env substitution
- [x] Update `Dockerfile` to use entrypoint
- [x] Update frontend Terraform for backend_url
- [x] Create `useFeatures.ts` hook

### Phase 4: CI/CD Simplification

- [x] Create `validation.yml`
- [x] Create `deploy.yml`
- [x] Create `cleanup.yml`
- [x] Create `production.yml`
- [ ] Delete old workflows (after testing)

### Phase 5: Docker Compose Profiles

- [x] Add profiles to services in `docker-compose.yml`
- [x] Create `scripts/dev.sh`
- [x] Update `package.json` dev script

### Phase 6: Terraform Feature Integration

- [x] Add feature variables to backend terraform
- [x] Make Redis/Temporal resources conditional
- [x] Add backend_url to frontend terraform
- [x] Add feature variables to worker terraform

## Remaining Work

### Delete Old Workflows (after testing)

After verifying the new workflows work correctly, delete:

- `.github/workflows/_backend.yml`
- `.github/workflows/_frontend.yml`
- `.github/workflows/_worker.yml`
- `.github/workflows/backend-deploy.yml`
- `.github/workflows/frontend-deploy.yml`
- `.github/workflows/worker-deploy.yml`
- `.github/workflows/deploy-all.yml`
- `.github/workflows/destroy-services.yml`
- `.github/workflows/database-destroy.yml`
- `.github/workflows/pr-validation.yml` (replaced by validation.yml)

Keep:

- `.github/workflows/_neon.yml` (reused by deploy/cleanup)

## Verification Checklist

### Local Dev

```bash
# Test default features (redis/temporal disabled)
pnpm dev
# Should start: backend, frontend only

# Test with redis enabled
# Edit features.json: "redis": true
pnpm dev
# Should start: backend, frontend, redis, worker, redis-insight

# Test all services
pnpm dev:all
# Should start all services
```

### Backend Features Endpoint

```bash
curl http://localhost:8080/api/features
# Expected: {"redis":false,"worker":false,"temporal":false,"llm":{...}}
```

### Docker Build with Features

```bash
# Build lean image (no optional deps)
docker build \
  --build-arg FEATURE_REDIS=false \
  --build-arg FEATURE_TEMPORAL=false \
  -f services/backend/Dockerfile .

# Build with all features
docker build \
  --build-arg FEATURE_REDIS=true \
  --build-arg FEATURE_TEMPORAL=true \
  --build-arg FEATURE_LLM_OPENAI=true \
  -f services/backend/Dockerfile .
```

### CI/CD

1. Create PR → validation.yml runs
2. Manual trigger deploy.yml → creates environment
3. Manual trigger cleanup.yml → destroys environment
4. Push to main → production.yml auto-deploys
