resource "google_storage_bucket" "scraper-bucket" {
  name                        = "scraper-rentals-data"
  location                    = var.region
  force_destroy               = false
  project                     = var.project_id
  storage_class               = "STANDARD"

  lifecycle_rule {
    condition {
      age        = 30
      with_state = "LIVE"
    }
    action {
      type = "Delete"
    }
  }

  versioning {
    enabled = true
  }

  labels = {
    managed_by = "terraform"
  }

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  soft_delete_policy {
    retention_duration_seconds = 7 * 24 * 60 * 60
  }

}
