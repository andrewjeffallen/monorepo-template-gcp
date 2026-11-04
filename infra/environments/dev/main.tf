# Development environment configuration
# This is a minimal setup optimized for GCP free tier

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Uncomment to use GCS backend (recommended for team collaboration)
  # backend "gcs" {
  #   bucket = "moose-labs-terraform-state"
  #   prefix = "dev"
  # }
}

# Variables
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

# Configure the Google provider
provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  environment = "dev"
  labels = {
    environment = local.environment
    managed_by  = "opentofu"
    project     = "moose-labs"
  }
}

# =============================================================================
# Artifact Registry for Docker images
# =============================================================================
module "artifact_registry" {
  source = "../../modules/artifact-registry"

  project_id    = var.project_id
  region        = var.region
  repository_id = "moose-labs-${local.environment}"
  labels        = local.labels
}

# =============================================================================
# Enable required APIs
# =============================================================================
resource "google_project_service" "required_apis" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "firestore.googleapis.com",
    "pubsub.googleapis.com",
    "storage.googleapis.com",
  ])

  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

# =============================================================================
# Outputs
# =============================================================================
output "docker_repository_url" {
  description = "Docker repository URL for pushing images"
  value       = module.artifact_registry.repository_url
}

output "region" {
  description = "GCP region"
  value       = var.region
}

output "project_id" {
  description = "GCP project ID"
  value       = var.project_id
}
