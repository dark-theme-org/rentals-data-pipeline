resource "google_service_account" "sa" {
  account_id   = "${var.project_id}-sa"
  display_name = format("%s service account", var.project_id)
}

resource "google_storage_bucket_iam_member" "sa" {
  bucket = google_storage_bucket.scraper-bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.sa.email}"
}
