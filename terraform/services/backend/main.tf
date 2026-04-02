# Backend Service Infrastructure
# Deploys: Artifact Registry + GCS Bucket + Cloud Run + Migration Job

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.0"
    }
  }

  # State storage in GCS bucket (configured via backend-config in CI/CD)
  backend "gcs" {
    prefix = "terraform/services/backend"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  service_name   = "${var.app_name}-backend-${var.environment}"
  sanitized_name = lower(replace(local.service_name, "_", "-"))

  # Helper to prefix names starting with a number (required by GCP, Temporal)
  # Usage: can(regex("^[0-9]", name)) ? "app-${name}" : name
  app_name_sanitized = can(regex("^[0-9]", var.app_name)) ? "app-${var.app_name}" : var.app_name

  # Generate unique bucket suffix
  bucket_suffix = substr(md5("${var.project_id}-${var.app_name}"), 0, 4)
  bucket_name   = "${local.app_name_sanitized}-${var.environment}-${local.bucket_suffix}"

  # Redis URL from Redis Cloud (provided via CI/CD secret)
  redis_url = var.feature_redis ? var.redis_url : ""

  # ─────────────────────────────────────────────────────────────────────────────
  # Temporal Cloud Configuration
  # ─────────────────────────────────────────────────────────────────────────────

  # Sanitize environment name (remove special chars, limit length)
  sanitized_environment = substr(
    replace(lower(var.environment), "/[^a-z0-9-]/", "-"),
    0, 20
  )

  # Namespace: {app}-{env}-{hash} (e.g., myapp-prod-9ab1, myapp-feature-x-9ab1)
  # Each branch gets its own namespace - no sharing conflicts
  # Temporal Cloud has a 39-char limit, so truncate app name to fit
  temporal_max_app_len    = 39 - 1 - length(local.sanitized_environment) - 1 - 4
  temporal_app_name       = trimsuffix(substr(local.app_name_sanitized, 0, local.temporal_max_app_len), "-")
  temporal_namespace_name = "${local.temporal_app_name}-${local.sanitized_environment}-${local.bucket_suffix}"

  # Task queue: same for all environments (namespace provides isolation)
  temporal_task_queue_name = "${local.app_name_sanitized}-tasks"

  # Construct Temporal address from region (Temporal Cloud uses regional endpoints)
  # Transform aws-ap-southeast-1 -> ap-southeast-1.aws.api.temporal.io:7233
  # Only compute if feature_temporal is enabled
  temporal_region_parts = var.feature_temporal && var.temporal_api_key != "" ? split("-", var.temporal_region) : []
  temporal_cloud_prefix = length(local.temporal_region_parts) > 0 ? local.temporal_region_parts[0] : ""
  temporal_cloud_region = length(local.temporal_region_parts) > 1 ? join("-", slice(local.temporal_region_parts, 1, length(local.temporal_region_parts))) : ""
  temporal_address = var.feature_temporal ? (
    var.temporal_api_key != "" ? (
      "${local.temporal_cloud_region}.${local.temporal_cloud_prefix}.api.temporal.io:7233"
    ) : var.temporal_address
  ) : ""

  # Namespace name - use computed name if API key is set, otherwise use provided value
  # The namespace is created by CI/CD via Temporal Cloud API
  # For Temporal Cloud, namespace must include account ID suffix (e.g., myapp-prod-abc1.xtjkf)
  temporal_namespace = var.feature_temporal && var.temporal_api_key != "" ? (
    var.temporal_account_id != "" ? "${local.temporal_namespace_name}.${var.temporal_account_id}" : local.temporal_namespace_name
  ) : var.temporal_namespace

  temporal_task_queue = var.feature_temporal && var.temporal_api_key != "" ? (
    local.temporal_task_queue_name
  ) : var.temporal_task_queue
}

# Note: Artifact Registry is created by the build step via gcloud CLI
# This avoids state management conflicts with Terraform

# Note: Redis is provided externally via Redis Cloud
# REDIS_URL is passed as a secret per environment

# ─────────────────────────────────────────────────────────────────────────────
# Temporal Cloud Namespace
# NOTE: Namespace creation is handled in CI/CD via Temporal Cloud API
# This avoids provider initialization issues when temporal is disabled
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# GCS Storage Bucket
# ─────────────────────────────────────────────────────────────────────────────

module "storage" {
  source = "../../modules/gcs"

  name         = local.bucket_name
  project_id   = var.project_id
  region       = var.region
  cors_origins = var.cors_origins

  force_destroy            = var.environment != "prod"
  public_access_prevention = "enforced"

  labels = {
    environment = var.environment
    service     = "backend"
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Cloud Run Service
# ─────────────────────────────────────────────────────────────────────────────

module "cloud_run" {
  source = "../../modules/cloud-run"

  name       = local.service_name
  project_id = var.project_id
  region     = var.region
  image_url  = var.image_url
  port       = var.backend_port

  cpu_limit             = var.cpu_limit
  memory_limit          = var.memory_limit
  min_instances         = var.min_instances
  max_instances         = var.max_instances
  container_concurrency = var.container_concurrency
  timeout_seconds       = var.timeout_seconds
  cpu_idle              = true

  allow_public_access = true

  env_vars = merge(
    {
      ENV              = var.env
      DEBUG            = var.debug
      BACKEND_PORT     = tostring(var.backend_port)
      GCP_PROJECT_ID   = var.project_id
      STORAGE_PROVIDER = "gcp"
      GCS_BUCKET_NAME  = module.storage.name
      CORS_ORIGINS     = join(",", var.cors_origins)
      LOG_LEVEL        = var.log_level
      # Feature flags
      FEATURE_REDIS    = tostring(var.feature_redis)
      FEATURE_WORKER   = tostring(var.feature_worker)
      FEATURE_TEMPORAL = tostring(var.feature_temporal)
    },
    # Only include optional vars if they're set
    var.database_url != "" ? { DATABASE_URL = var.database_url } : {},
    local.redis_url != "" ? { REDIS_URL = local.redis_url } : {},
    var.redis_key_prefix != "" ? { REDIS_KEY_PREFIX = var.redis_key_prefix } : {},
    var.openai_api_key != "" ? { OPENAI_API_KEY = var.openai_api_key } : {},
    var.anthropic_api_key != "" ? { ANTHROPIC_API_KEY = var.anthropic_api_key } : {},
    var.gemini_api_key != "" ? { GEMINI_API_KEY = var.gemini_api_key } : {},
    var.clerk_secret_key != "" ? { CLERK_SECRET_KEY = var.clerk_secret_key } : {},
    var.clerk_webhook_secret != "" ? { CLERK_WEBHOOK_SECRET = var.clerk_webhook_secret } : {},
    var.google_service_account_json != "" ? { GOOGLE_SERVICE_ACCOUNT_JSON = var.google_service_account_json } : {},
    # Langfuse - LLM Observability (optional)
    var.langfuse_public_key != "" ? { LANGFUSE_PUBLIC_KEY = var.langfuse_public_key } : {},
    var.langfuse_secret_key != "" ? { LANGFUSE_SECRET_KEY = var.langfuse_secret_key } : {},
    var.langfuse_public_key != "" ? { LANGFUSE_HOST = var.langfuse_host } : {},
    # Temporal Cloud (optional) - uses auto-created namespace if api_key provided
    local.temporal_address != "" ? { TEMPORAL_ADDRESS = local.temporal_address } : {},
    local.temporal_namespace != "" ? { TEMPORAL_NAMESPACE = local.temporal_namespace } : {},
    var.temporal_api_key != "" ? { TEMPORAL_API_KEY = var.temporal_api_key } : {},
    local.temporal_task_queue != "" ? { TEMPORAL_TASK_QUEUE = local.temporal_task_queue } : {},
    # Worker URL for HTTP activation (enables scale-to-zero)
    var.worker_url != "" ? { WORKER_URL = var.worker_url } : {},
    var.extra_env_vars,
  )

  startup_probe = {
    path                  = "/api/health"
    initial_delay_seconds = 5
    timeout_seconds       = 5
    period_seconds        = 10
    failure_threshold     = 6 # Total: 5 + (6 * 10) = 65 seconds
  }

  startup_cpu_boost = true
}

# ─────────────────────────────────────────────────────────────────────────────
# Database Migration Job
# ─────────────────────────────────────────────────────────────────────────────

resource "google_cloud_run_v2_job" "migration" {
  count    = var.database_url != "" ? 1 : 0
  name     = "${module.cloud_run.service_name}-migration"
  location = var.region
  project  = var.project_id

  template {
    template {
      containers {
        image = var.image_url
        # Use venv directly - uv is not installed in production image
        command     = ["/app/.venv/bin/alembic", "-c", "/packages/db/alembic.ini", "upgrade", "head"]
        working_dir = "/app"

        env {
          name  = "DATABASE_URL"
          value = var.database_url
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }
      }

      timeout     = "300s"
      max_retries = 2
    }
  }

  depends_on = [module.cloud_run]
}
