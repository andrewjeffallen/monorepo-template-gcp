# Artifact Registry module for Docker image storage

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "repository_id" {
  description = "Repository ID"
  type        = string
  default     = "moose-labs"
}

variable "labels" {
  description = "Labels to apply to the repository"
  type        = map(string)
  default     = {}
}

resource "google_artifact_registry_repository" "docker" {
  project       = var.project_id
  location      = var.region
  repository_id = var.repository_id
  description   = "Docker repository for Moose Labs services"
  format        = "DOCKER"

  labels = var.labels

  # Cleanup policy to manage storage costs (free tier friendly)
  cleanup_policies {
    id     = "delete-old-images"
    action = "DELETE"
    condition {
      older_than = "2592000s" # 30 days
      tag_state  = "UNTAGGED"
    }
  }

  cleanup_policies {
    id     = "keep-minimum-versions"
    action = "KEEP"
    most_recent_versions {
      keep_count = 5
    }
  }
}

output "repository_url" {
  description = "Docker repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}

output "repository_id" {
  description = "Repository ID"
  value       = google_artifact_registry_repository.docker.repository_id
}
