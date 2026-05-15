# IAM resources: service account, bucket and registry bindings, and developer token creator grants.

resource "google_service_account" "sa" {
  account_id   = "${local.project_id}-sa"
  display_name = format("%s Service Account", local.project_id)
  description  = "Project SA to manage cloud resources"
}

resource "google_storage_bucket_iam_member" "sa_bucket" {
  bucket = google_storage_bucket.scraper-bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.sa.email}"
}

resource "google_artifact_registry_repository_iam_member" "sa_registry" {
  location   = google_artifact_registry_repository.pipeline_images.location
  repository = google_artifact_registry_repository.pipeline_images.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.sa.email}"
}

resource "google_project_iam_member" "sa_run_developer" {
  project = local.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.sa.email}"
}

resource "google_service_account_iam_member" "sa_token_creator" {
  for_each           = toset(var.developer_principals)
  service_account_id = google_service_account.sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = each.value
}
