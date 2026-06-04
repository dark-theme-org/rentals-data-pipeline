# Terraform backend and provider configuration.

terraform {
  required_version = ">= 1.6.0, < 2.0.0"

  backend "gcs" {
    bucket = "dark-tfstates"
    prefix = "rentals-data-pipeline"  # must match cloud/settings.yml project_id — backend blocks cannot use locals or file()
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.10"
    }
  }
}

provider "google" {
  project = local.project_id
  region  = local.location
}
