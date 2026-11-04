# Networking module for VPC and related resources
# Useful for private Cloud Run, Cloud SQL, etc.

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "network_name" {
  description = "VPC network name"
  type        = string
  default     = "moose-labs-vpc"
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}

# VPC Network
resource "google_compute_network" "vpc" {
  project                 = var.project_id
  name                    = var.network_name
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

# Subnet for services
resource "google_compute_subnetwork" "services" {
  project       = var.project_id
  name          = "${var.network_name}-services"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id

  private_ip_google_access = true
}

# Serverless VPC Access connector (for Cloud Run -> private resources)
resource "google_vpc_access_connector" "connector" {
  project       = var.project_id
  name          = "${var.network_name}-connector"
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = "10.8.0.0/28"

  # Free tier friendly: min throughput
  min_throughput = 200
  max_throughput = 300
}

output "network_id" {
  description = "VPC network ID"
  value       = google_compute_network.vpc.id
}

output "network_name" {
  description = "VPC network name"
  value       = google_compute_network.vpc.name
}

output "subnet_id" {
  description = "Services subnet ID"
  value       = google_compute_subnetwork.services.id
}

output "vpc_connector_id" {
  description = "VPC Access connector ID"
  value       = google_vpc_access_connector.connector.id
}
