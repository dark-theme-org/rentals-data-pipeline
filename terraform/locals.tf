# Computed locals shared across all Terraform resources.

locals {
  _settings  = yamldecode(file("${path.module}/../cloud/settings.yml"))
  project_id = local._settings.project_id
  region     = local._settings.region

  labels = {
    managed_by = "terraform"
  }

  developers = local._settings.developers
}
