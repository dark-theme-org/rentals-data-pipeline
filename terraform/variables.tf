variable "project_id" {
  type        = string
  description = "GCP project ID. Doubles as the GCS bucket name (project IDs are globally unique)."
  default     = "rentals-data-pipeline"
}

variable "region" {
  type        = string
  description = "GCP region for the bucket."
  default     = "us-central1"
}
