# Artifact Registry repository for pipeline Docker images.

locals {
  registry_format = "DOCKER"
}

resource "google_artifact_registry_repository" "pipeline_images" {
  location      = local.location
  repository_id = "${local.project_id}-${lower(local.registry_format)}"
  format        = local.registry_format
  description   = format("Artifact registry repository with %s format for %s project", local.registry_format, local.project_id)

  docker_config {
    immutable_tags = false
  }

  labels = local.labels
}
