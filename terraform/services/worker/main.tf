# Worker Service Infrastructure
# Deploys: Artifact Registry + Cloud Run

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
    prefix = "terraform/services/worker"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  service_name   = "${var.app_name}-worker-${var.environment}"
  sanitized_name = lower(replace(local.service_name, "_", "-"))

  # Helper to prefix names starting with a number (required by GCP, Temporal)
  app_name_sanitized = can(regex("^[0-9]", var.app_name)) ? "app-${var.app_name}" : var.app_name

  # Generate unique suffix (same formula as backend)
  bucket_suffix = substr(md5("${var.project_id}-${var.app_name}"), 0, 4)

  # ─────────────────────────────────────────────────────────────────────────────
  # Temporal Cloud Configuration (same formulas as backend)
  # Worker computes these independently to allow deploying before backend
  # ─────────────────────────────────────────────────────────────────────────────

  # Sanitize environment name (remove special chars, limit length)
  sanitized_environment = substr(
    replace(lower(var.environment), "/[^a-z0-9-]/", "-"),
    0, 20
  )

  # Namespace: {app}-{env}-{hash}.{account_id}
  # Temporal Cloud has a 39-char limit, so truncate app name to fit
  temporal_max_app_len    = 39 - 1 - length(local.sanitized_environment) - 1 - 4
  temporal_app_name       = trimsuffix(substr(local.app_name_sanitized, 0, local.temporal_max_app_len), "-")
  temporal_namespace_name = "${local.temporal_app_name}-${local.sanitized_environment}-${local.bucket_suffix}"

  # Task queue: same for all environments
  temporal_task_queue_name = "${local.app_name_sanitized}-tasks"

  # Construct Temporal address from region
  # Transform aws-ap-southeast-1 -> ap-southeast-1.aws.api.temporal.io:7233
  temporal_region_parts = var.feature_temporal && var.temporal_api_key != "" ? split("-", var.temporal_region) : []
  temporal_cloud_prefix = length(local.temporal_region_parts) > 0 ? local.temporal_region_parts[0] : ""
  temporal_cloud_region = length(local.temporal_region_parts) > 1 ? join("-", slice(local.temporal_region_parts, 1, length(local.temporal_region_parts))) : ""

  # Computed values (only when Temporal Cloud is enabled)
  temporal_address = var.feature_temporal && var.temporal_api_key != "" ? (
    "${local.temporal_cloud_region}.${local.temporal_cloud_prefix}.api.temporal.io:7233"
  ) : var.temporal_address

  temporal_namespace = var.feature_temporal && var.temporal_api_key != "" ? (
    var.temporal_account_id != "" ? "${local.temporal_namespace_name}.${var.temporal_account_id}" : local.temporal_namespace_name
  ) : var.temporal_namespace

  temporal_task_queue = var.feature_temporal && var.temporal_api_key != "" ? (
    local.temporal_task_queue_name
  ) : var.temporal_task_queue
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
  port       = var.worker_port

  cpu_limit             = var.cpu_limit
  memory_limit          = var.memory_limit
  min_instances         = var.min_instances
  max_instances         = var.max_instances
  container_concurrency = var.container_concurrency
  timeout_seconds       = var.timeout_seconds
  cpu_idle              = false  # Must be false for Temporal worker (continuous polling)
  startup_cpu_boost     = true   # Speed up initialization

  allow_public_access = true # Required for HTTP activation (backend calls /wakeup)

  env_vars = merge(
    {
      ENV            = var.env
      DEBUG          = var.debug
      LOG_LEVEL      = var.log_level
      GCP_PROJECT_ID = var.project_id
    },
    var.redis_url != "" ? { REDIS_URL = var.redis_url } : {},
    var.redis_key_prefix != "" ? { REDIS_KEY_PREFIX = var.redis_key_prefix } : {},
    var.database_url != "" ? { DATABASE_URL = var.database_url } : {},
    # Temporal Cloud (computed or passed)
    var.feature_temporal ? { FEATURE_TEMPORAL = "true" } : {},
    local.temporal_address != "" ? { TEMPORAL_ADDRESS = local.temporal_address } : {},
    local.temporal_namespace != "" ? { TEMPORAL_NAMESPACE = local.temporal_namespace } : {},
    var.temporal_api_key != "" ? { TEMPORAL_API_KEY = var.temporal_api_key } : {},
    local.temporal_task_queue != "" ? { TEMPORAL_TASK_QUEUE = local.temporal_task_queue } : {},
    var.extra_env_vars,
  )

  # Allow more time for DB/Redis cold start connections
  startup_probe = {
    path                  = "/health"
    initial_delay_seconds = 10
    timeout_seconds       = 5
    period_seconds        = 15
    failure_threshold     = 6  # Total: 10 + (6 * 15) = 100 seconds
  }
}
