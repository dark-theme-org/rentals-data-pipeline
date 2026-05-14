variable "region" {
  type        = string
  description = "Region for GCP resources."
  default     = "us-central1"
}

variable "developer_principals" {
  type        = list(string)
  description = "Principals users granted `roles/iam.serviceAccountTokenCreator` so they can run the entrypoint locally via ADC impersonation. Configure per-developer in the gitignored `terraform.tfvars`; never commit individual emails."
  default     = []
}
