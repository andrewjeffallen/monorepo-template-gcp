# Cloud Run service module

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
}

variable "image" {
  description = "Container image URL"
  type        = string
}

variable "port" {
  description = "Container port"
  type        = number
  default     = 8080
}

variable "cpu" {
  description = "CPU allocation (e.g., '1' or '1000m')"
  type        = string
  default     = "1"
}

variable "memory" {
  description = "Memory allocation (e.g., '512Mi', '1Gi')"
  type        = string
  default     = "512Mi"
}

variable "min_instances" {
  description = "Minimum number of instances (0 for scale to zero)"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = number
  default     = 2
}

variable "env_vars" {
  description = "Environment variables"
  type        = map(string)
  default     = {}
}

variable "allow_unauthenticated" {
  description = "Allow unauthenticated access"
  type        = bool
  default     = false
}

variable "labels" {
  description = "Labels to apply to the service"
  type        = map(string)
  default     = {}
}

resource "google_cloud_run_v2_service" "service" {
  project  = var.project_id
  name     = var.service_name
  location = var.region

  labels = var.labels

  template {
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.image

      ports {
        container_port = var.port
      }

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
        cpu_idle = true # Scale to zero friendly
      }

      dynamic "env" {
        for_each = var.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }

      # Health check
      startup_probe {
        http_get {
          path = "/health"
          port = var.port
        }
        initial_delay_seconds = 5
        period_seconds        = 10
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = var.port
        }
        period_seconds    = 30
        failure_threshold = 3
      }
    }
  }

  # Traffic configuration
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# IAM binding for public access (if enabled)
resource "google_cloud_run_v2_service_iam_member" "public" {
  count = var.allow_unauthenticated ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.service.uri
}

output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.service.name
}
