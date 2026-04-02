# Cloud Run Module - Variables

variable "name" {
  description = "Service name (will be sanitized for Cloud Run requirements)"
  type        = string
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "image_url" {
  description = "Full Docker image URL (e.g., us-docker.pkg.dev/project/repo/image:tag)"
  type        = string
}

variable "port" {
  description = "Container port"
  type        = number
  default     = 8080
}

variable "env_vars" {
  description = "Environment variables as key-value map"
  type        = map(string)
  default     = {}
}

variable "secret_env_vars" {
  description = "Secret environment variables from Secret Manager"
  type = map(object({
    secret_name = string
    version     = string
  }))
  default = {}
}

variable "cpu_limit" {
  description = "CPU limit (e.g., '1', '2', '4')"
  type        = string
  default     = "1"
}

variable "memory_limit" {
  description = "Memory limit (e.g., '512Mi', '1Gi', '2Gi')"
  type        = string
  default     = "512Mi"
}

variable "cpu_idle" {
  description = "Whether CPU is throttled when there are no requests"
  type        = bool
  default     = true
}

variable "startup_cpu_boost" {
  description = "Whether to boost CPU during startup"
  type        = bool
  default     = false
}

variable "min_instances" {
  description = "Minimum number of instances"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = number
  default     = 10
}

variable "container_concurrency" {
  description = "Max concurrent requests per instance"
  type        = number
  default     = 100
}

variable "timeout_seconds" {
  description = "Request timeout in seconds"
  type        = number
  default     = 300
}

variable "allow_public_access" {
  description = "Whether to allow unauthenticated access"
  type        = bool
  default     = true
}

variable "service_account_email" {
  description = "Service account email for the Cloud Run service"
  type        = string
  default     = null
}

variable "startup_probe" {
  description = "Startup probe configuration"
  type = object({
    path                  = string
    initial_delay_seconds = optional(number, 0)
    timeout_seconds       = optional(number, 1)
    period_seconds        = optional(number, 3)
    failure_threshold     = optional(number, 3)
  })
  default = null
}

variable "liveness_probe" {
  description = "Liveness probe configuration"
  type = object({
    path                  = string
    initial_delay_seconds = optional(number, 0)
    timeout_seconds       = optional(number, 1)
    period_seconds        = optional(number, 10)
    failure_threshold     = optional(number, 3)
  })
  default = null
}

variable "vpc_connector" {
  description = "VPC Access Connector name for connecting to VPC resources (e.g., self-hosted Redis)"
  type        = string
  default     = null
}

variable "vpc_egress" {
  description = "VPC egress setting (ALL_TRAFFIC or PRIVATE_RANGES_ONLY)"
  type        = string
  default     = "PRIVATE_RANGES_ONLY"
}

