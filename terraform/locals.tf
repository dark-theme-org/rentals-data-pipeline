locals {
  project_id = trimspace(file("${path.module}/../.google-project-id"))

  labels = {
    managed_by = "terraform"
  }
}
