# BigQuery resources for rentals data pipeline.

resource "google_bigquery_dataset" "dataset" {
  for_each   = local.environments
  dataset_id = each.value
  location   = local.region
  project    = local.project_id
  labels     = local.labels
}

