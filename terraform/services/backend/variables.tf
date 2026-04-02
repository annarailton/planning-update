# Backend Service - Variables

# ─────────────────────────────────────────────────────────────────────────────
# Feature Flags (from features.json via CI/CD)
# ─────────────────────────────────────────────────────────────────────────────

variable "feature_redis" {
  description = "Enable Redis features (jobs, queues, pub/sub)"
  type        = bool
  default     = false
}

variable "feature_temporal" {
  description = "Enable Temporal workflow orchestration"
  type        = bool
  default     = false
}

variable "feature_worker" {
  description = "Enable background worker service"
  type        = bool
  default     = false
}

variable "feature_langfuse" {
  description = "Enable Langfuse LLM observability"
  type        = bool
  default     = false
}

# ─────────────────────────────────────────────────────────────────────────────
# Required Variables
# ─────────────────────────────────────────────────────────────────────────────

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod, or branch name)"
  type        = string
}

variable "image_url" {
  description = "Full Docker image URL (built by GitHub Actions)"
  type        = string
}

# ─────────────────────────────────────────────────────────────────────────────
# Optional Configuration
# ─────────────────────────────────────────────────────────────────────────────

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "app"
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "asia-southeast1"
}

# ─────────────────────────────────────────────────────────────────────────────
# Cloud Run Configuration
# ─────────────────────────────────────────────────────────────────────────────

variable "backend_port" {
  description = "Backend service port"
  type        = number
  default     = 8080
}

variable "cpu_limit" {
  description = "CPU limit"
  type        = string
  default     = "1"
}

variable "memory_limit" {
  description = "Memory limit"
  type        = string
  default     = "1Gi"
}

variable "min_instances" {
  description = "Minimum instances"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum instances"
  type        = number
  default     = 10
}

variable "container_concurrency" {
  description = "Max concurrent requests per instance"
  type        = number
  default     = 100
}

variable "timeout_seconds" {
  description = "Request timeout"
  type        = number
  default     = 300
}

# ─────────────────────────────────────────────────────────────────────────────
# Application Configuration
# ─────────────────────────────────────────────────────────────────────────────

variable "env" {
  description = "Application environment (development, staging, production)"
  type        = string
  default     = "production"
}

variable "debug" {
  description = "Debug mode"
  type        = string
  default     = "false"
}

variable "log_level" {
  description = "Log level"
  type        = string
  default     = "INFO"
}

variable "cors_origins" {
  description = "CORS allowed origins"
  type        = list(string)
  default     = ["*"]
}

# ─────────────────────────────────────────────────────────────────────────────
# Secrets (passed via TF_VAR_* environment variables)
# ─────────────────────────────────────────────────────────────────────────────

variable "database_url" {
  description = "Database connection URL"
  type        = string
  sensitive   = true
  default     = ""
}

variable "redis_url" {
  description = "Redis Cloud connection URL (set per environment via GitHub secrets)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "anthropic_api_key" {
  description = "Anthropic API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "gemini_api_key" {
  description = "Google Gemini API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "clerk_secret_key" {
  description = "Clerk secret key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "clerk_webhook_secret" {
  description = "Clerk webhook secret"
  type        = string
  sensitive   = true
  default     = ""
}

variable "google_service_account_json" {
  description = "Service account JSON for GCS signed URLs"
  type        = string
  sensitive   = true
  default     = ""
}

# ─────────────────────────────────────────────────────────────────────────────
# Langfuse - LLM Observability (Optional)
# ─────────────────────────────────────────────────────────────────────────────

variable "langfuse_public_key" {
  description = "Langfuse public key (optional - enables LLM tracing)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "langfuse_secret_key" {
  description = "Langfuse secret key (optional - enables LLM tracing)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "langfuse_host" {
  description = "Langfuse host URL"
  type        = string
  default     = "https://cloud.langfuse.com"
}

# ─────────────────────────────────────────────────────────────────────────────
# Temporal Cloud Configuration (Optional)
# ─────────────────────────────────────────────────────────────────────────────

variable "temporal_address" {
  description = "Temporal Cloud address (computed automatically if temporal_api_key is set)"
  type        = string
  default     = ""
}

variable "temporal_namespace" {
  description = "Temporal namespace (computed automatically if temporal_api_key is set)"
  type        = string
  default     = ""
}

variable "temporal_api_key" {
  description = "Temporal Cloud API key (enables Temporal Cloud if set)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "temporal_task_queue" {
  description = "Temporal task queue name (computed automatically if temporal_api_key is set)"
  type        = string
  default     = ""
}

variable "temporal_account_id" {
  description = "Temporal Cloud account ID (the suffix after namespace name, e.g., 'xtjkf' for namespace.xtjkf)"
  type        = string
  default     = ""
}

variable "temporal_region" {
  description = <<-EOT
    Temporal Cloud region in format: {cloud}-{region}

    AWS regions:
      - aws-us-east-1 (N. Virginia)
      - aws-us-west-2 (Oregon)
      - aws-eu-west-1 (Ireland)
      - aws-eu-west-2 (London)
      - aws-eu-central-1 (Frankfurt)
      - aws-ap-southeast-1 (Singapore)
      - aws-ap-southeast-2 (Sydney)
      - aws-ap-northeast-1 (Tokyo)

    GCP regions:
      - gcp-us-central1
      - gcp-europe-west1

    Transforms to endpoint: {region}.{cloud}.api.temporal.io:7233
  EOT
  type        = string
  default     = "aws-ap-southeast-1"

  validation {
    condition     = can(regex("^(aws|gcp)-", var.temporal_region))
    error_message = "Region must start with 'aws-' or 'gcp-' (e.g., aws-eu-west-2, gcp-us-central1)"
  }
}

variable "temporal_retention_days" {
  description = "Workflow history retention period in days"
  type        = number
  default     = 7
}

# ─────────────────────────────────────────────────────────────────────────────
# Worker Service Configuration (for HTTP activation)
# ─────────────────────────────────────────────────────────────────────────────

variable "worker_url" {
  description = "Worker service URL for HTTP activation (enables scale-to-zero for workers)"
  type        = string
  default     = ""
}

variable "redis_key_prefix" {
  description = "Redis key prefix for environment isolation (e.g., 'prod:', 'staging:', 'feature-x:')"
  type        = string
  default     = ""
}

variable "extra_env_vars" {
  description = "Additional environment variables"
  type        = map(string)
  default     = {}
}
