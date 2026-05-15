# Input variables for the Terraform stack.

variable "developer_principals" {
  type        = list(string)
  description = "Principals users granted `roles/iam.serviceAccountTokenCreator` so they can run the entrypoint locally via ADC impersonation. Configure per-developer in the gitignored `terraform.tfvars`; never commit individual emails."
  default     = []
}
