terraform {
  required_version = ">= 1.6.0, < 2.0.0"

  backend "gcs" {
    bucket = "dark-tfstates"
    prefix = "rentals-data-pipeline"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.10"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
