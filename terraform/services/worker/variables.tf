# Worker Service - Variables

# ─────────────────────────────────────────────────────────────────────────────
# Feature Flags (from features.json via CI/CD)
# ─────────────────────────────────────────────────────────────────────────────

variable "feature_temporal" {
  description = "Enable Temporal workflow orchestration"
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

variable "worker_port" {
  description = "Worker service port"
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
  default     = 5
}

variable "container_concurrency" {
  description = "Max concurrent requests per instance"
  type        = number
  default     = 10 # Lower for worker to process jobs sequentially
}

variable "timeout_seconds" {
  description = "Request timeout"
  type        = number
  default     = 900 # 15 minutes for long-running jobs
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

# ─────────────────────────────────────────────────────────────────────────────
# Redis Configuration (passed from backend)
# ─────────────────────────────────────────────────────────────────────────────

variable "redis_url" {
  description = "Redis connection URL (from backend's terraform output)"
  type        = string
  sensitive   = true
  default     = ""
}

# ─────────────────────────────────────────────────────────────────────────────
# Database Configuration
# ─────────────────────────────────────────────────────────────────────────────

variable "database_url" {
  description = "Database connection URL"
  type        = string
  sensitive   = true
  default     = ""
}

# ─────────────────────────────────────────────────────────────────────────────
# Temporal Cloud Configuration (Optional)
# ─────────────────────────────────────────────────────────────────────────────

variable "temporal_address" {
  description = "Temporal Cloud address (e.g., ap-southeast-1.aws.api.temporal.io:7233)"
  type        = string
  default     = ""
}

variable "temporal_namespace" {
  description = "Temporal namespace (e.g., myapp-prod-9ab1)"
  type        = string
  default     = ""
}

variable "temporal_api_key" {
  description = "Temporal Cloud API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "temporal_task_queue" {
  description = "Temporal task queue name"
  type        = string
  default     = ""
}

variable "temporal_region" {
  description = "Temporal Cloud region (e.g., aws-ap-southeast-1)"
  type        = string
  default     = "aws-ap-southeast-1"
}

variable "temporal_account_id" {
  description = "Temporal Cloud account ID (the suffix after namespace name)"
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
