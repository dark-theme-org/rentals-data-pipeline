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

variable "developer_principals" {
  type        = list(string)
  description = "Principals (e.g. `user:alice@example.com`) granted `roles/iam.serviceAccountTokenCreator` on the pipeline SA so they can run the entrypoint locally via ADC impersonation. Configure per-developer in the gitignored `terraform.tfvars`; never commit individual emails."
  default     = []
}
