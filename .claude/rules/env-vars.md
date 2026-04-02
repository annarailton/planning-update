---
paths:
  - "environment/**"
  - "terraform/**"
  - ".github/workflows/**"
---

# Environment Variables

## Locations

1. `environment/.env.*.example` - Local dev examples
2. GitHub Secrets - CI/CD
3. `terraform/services/*/variables.tf` - Variable definition
4. `terraform/services/*/main.tf` - Pass to Cloud Run
5. `.github/workflows/_*.yml` - `TF_VAR_*` prefix

## Prefixes

- Frontend: `VITE_` prefix required
- Terraform: `TF_VAR_` prefix in GitHub Actions
- Sensitive: `sensitive = true` in Terraform

## Adding New Vars

1. Add to `environment/.env.backend.example`
2. Add to `core/config.py` Settings class
3. Add to `terraform/services/*/variables.tf`
4. Add to GitHub Secrets/Variables
5. Pass in workflow with `TF_VAR_` prefix
