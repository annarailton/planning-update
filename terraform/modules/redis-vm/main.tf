# Self-hosted Redis on GCP Compute Engine
# Runs Redis in Docker on an e2-micro VM with public IP

locals {
  vm_name = var.name
  zone    = "${var.region}-a"

  # Cloud-init config for creating data directory
  cloud_init = <<-EOF
    #cloud-config
    bootcmd:
      - mkdir -p /mnt/disks/redis-data
      - chmod 777 /mnt/disks/redis-data
  EOF
}

# ─────────────────────────────────────────────────────────────────────────────
# Static External IP for Redis VM
# ─────────────────────────────────────────────────────────────────────────────

resource "google_compute_address" "redis" {
  name         = "${local.vm_name}-ip"
  project      = var.project_id
  region       = var.region
  address_type = "EXTERNAL"
}

# ─────────────────────────────────────────────────────────────────────────────
# Firewall Rules
# ─────────────────────────────────────────────────────────────────────────────

# Allow Redis port (protected by password)
resource "google_compute_firewall" "redis" {
  name    = "${var.name}-allow-redis"
  project = var.project_id
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["6379"]
  }

  # Allow from anywhere (Redis password protects access)
  # Can restrict to Cloud Run IPs if needed
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["redis-server"]
}

# Allow SSH for debugging (optional)
resource "google_compute_firewall" "ssh" {
  count   = var.allow_ssh ? 1 : 0
  name    = "${var.name}-allow-ssh"
  project = var.project_id
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["redis-server"]
}

# ─────────────────────────────────────────────────────────────────────────────
# Compute Engine VM
# ─────────────────────────────────────────────────────────────────────────────

resource "google_compute_instance" "redis" {
  name         = local.vm_name
  project      = var.project_id
  zone         = local.zone
  machine_type = var.machine_type

  tags = ["redis-server"]

  boot_disk {
    initialize_params {
      image = "cos-cloud/cos-stable"
      size  = var.disk_size_gb
      type  = "pd-standard"
    }
  }

  network_interface {
    network = "default"

    access_config {
      nat_ip = google_compute_address.redis.address
    }
  }

  # Container-Optimized OS runs Docker automatically
  metadata = {
    gce-container-declaration = yamlencode({
      spec = {
        containers = [{
          name  = "redis"
          image = "redis:${var.redis_version}"
          args = concat(
            ["--maxmemory", var.redis_maxmemory],
            ["--maxmemory-policy", "allkeys-lru"],
            var.redis_persistence ? ["--appendonly", "yes"] : [],
            ["--requirepass", var.redis_password]
          )
          volumeMounts = var.redis_persistence ? [{
            name      = "redis-data"
            mountPath = "/data"
          }] : []
        }]
        volumes = var.redis_persistence ? [{
          name = "redis-data"
          hostPath = {
            path = "/mnt/disks/redis-data"
          }
        }] : []
        restartPolicy = "Always"
      }
    })

    # Create data directory on boot (only if persistence enabled)
    user-data = var.redis_persistence ? local.cloud_init : null
  }

  service_account {
    scopes = ["cloud-platform"]
  }

  scheduling {
    preemptible       = var.preemptible
    automatic_restart = !var.preemptible
  }

  labels = var.labels

  lifecycle {
    ignore_changes = [
      metadata["ssh-keys"],
    ]
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Outputs
# ─────────────────────────────────────────────────────────────────────────────

output "public_ip" {
  description = "Public IP address of the Redis VM"
  value       = google_compute_address.redis.address
}

output "redis_url" {
  description = "Redis connection URL"
  value       = "redis://:${var.redis_password}@${google_compute_address.redis.address}:6379"
  sensitive   = true
}

output "vm_name" {
  description = "Name of the Redis VM"
  value       = google_compute_instance.redis.name
}

output "zone" {
  description = "Zone where the VM is deployed"
  value       = local.zone
}
