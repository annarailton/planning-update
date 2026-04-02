# Redis VM Module - Variables

# ─────────────────────────────────────────────────────────────────────────────
# Required Variables
# ─────────────────────────────────────────────────────────────────────────────

variable "name" {
  description = "Base name for resources (e.g., app-dev)"
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

variable "redis_password" {
  description = "Redis password for authentication"
  type        = string
  sensitive   = true
}

# ─────────────────────────────────────────────────────────────────────────────
# VM Configuration
# ─────────────────────────────────────────────────────────────────────────────

variable "machine_type" {
  description = "GCE machine type (e2-micro for free tier in us-west1/us-east1/us-central1)"
  type        = string
  default     = "e2-micro"
}

variable "disk_size_gb" {
  description = "Boot disk size in GB"
  type        = number
  default     = 10
}

variable "preemptible" {
  description = "Use preemptible/spot VM (cheaper but can be terminated)"
  type        = bool
  default     = false
}

variable "allow_ssh" {
  description = "Allow SSH access for debugging"
  type        = bool
  default     = false
}

# ─────────────────────────────────────────────────────────────────────────────
# Redis Configuration
# ─────────────────────────────────────────────────────────────────────────────

variable "redis_version" {
  description = "Redis Docker image version"
  type        = string
  default     = "7-alpine"
}

variable "redis_maxmemory" {
  description = "Redis max memory (e.g., 256mb, 512mb)"
  type        = string
  default     = "256mb"
}

variable "redis_persistence" {
  description = "Enable Redis AOF persistence"
  type        = bool
  default     = true
}

# ─────────────────────────────────────────────────────────────────────────────
# Labels
# ─────────────────────────────────────────────────────────────────────────────

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}
