# Terraform

GCP infrastructure for the **Rentals Data Pipeline** project. Manages the
storage bucket, service account, IAM bindings, and Artifact Registry
repository. Remote state is stored in a shared GCS backend (`dark-tfstates`)
hosted in the `darktheme-ops` project.

> **Cloud Run Jobs and Cloud Workflows are deployed by `scripts/deploy.py`, not
> Terraform.** Terraform owns long-lived infrastructure; the deploy script owns
> the application layer.

## What this stack creates

| Resource | What it is |
| --- | --- |
| `google_storage_bucket.scraper-bucket` | `scraper-rentals-data` — regional in `southamerica-east1` (read from `cloud/settings.yml`), versioning on, lifecycle deletes live objects after 30 days, public access blocked |
| `google_artifact_registry_repository.pipeline_images` | `${project_id}-docker` — Docker image repository for Cloud Run Job images. `immutable_tags = false` allows the same tag to be overwritten across deploys. |
| `google_bigquery_dataset.dataset` | One BigQuery dataset per environment (`dev`, `test`, `prod`) — each dataset is the landing zone for the Bronze layer loaded by `gcs_to_bigquery_bronze`. |
| `google_service_account.sa` | `${project_id}-sa` — single runtime identity used by Cloud Run Jobs, Cloud Workflows, and local dev via ADC impersonation |
| `google_storage_bucket_iam_member.sa_bucket` | `storage.objectAdmin` on the data bucket |
| `google_artifact_registry_repository_iam_member.sa_registry` | `artifactregistry.reader` on the image repository |
| `google_project_iam_member.sa_run_developer` | `roles/run.developer` at project level — allows Cloud Workflows to trigger Cloud Run Jobs |
| `google_project_iam_member.sa_bq_job_user` | `roles/bigquery.jobUser` at project level — allows the SA to submit BigQuery load jobs |
| `google_bigquery_dataset_iam_member.sa_bq_data_editor` | `roles/bigquery.dataEditor` on each environment dataset — allows the SA to create tables and insert rows |
| `google_service_account_iam_member.sa_token_creator` | `iam.serviceAccountTokenCreator` on the SA for each principal in the `developers` list in `cloud/settings.yml` — enables local ADC impersonation |

## Files

| File | Purpose |
| --- | --- |
| [terraform.tf](terraform.tf) | Backend (`gs://dark-tfstates/rentals-data-pipeline`) and Google provider (`~> 6.10`). The backend `prefix` must match `project_id` in `cloud/settings.yml` — it cannot use locals or `file()`. |
| [locals.tf](locals.tf) | Reads `project_id`, `region`, `developers`, and `environments` from `cloud/settings.yml` via `yamldecode`; defines `labels = { managed_by = "terraform" }` shared across all resources. To grant yourself ADC impersonation, add your GCP principal to the `developers` list in `cloud/settings.yml`. |
| [gcs.tf](gcs.tf) | The data bucket and all bucket-level settings. |
| [bigquery.tf](bigquery.tf) | BigQuery datasets — one per environment (`dev`, `test`, `prod`), each scoped to the project region. |
| [registry.tf](registry.tf) | Artifact Registry Docker repository for pipeline images. |
| [iam.tf](iam.tf) | Service account, all IAM bindings, and developer token creator grants. |

## Prerequisites

- `terraform >= 1.6, < 2.0` and `gcloud` installed
- Application Default Credentials: `gcloud auth application-default login` — must be the account with access to both `darktheme-ops` (state) and `rentals-data-pipeline` (resources)
- The `darktheme-ops` project and `gs://dark-tfstates` state bucket exist (already bootstrapped)
- The `rentals-data-pipeline` project exists with billing linked and the following APIs enabled:

  ```bash
  gcloud services enable \
    storage.googleapis.com \
    iam.googleapis.com \
    iamcredentials.googleapis.com \
    artifactregistry.googleapis.com \
    run.googleapis.com \
    workflows.googleapis.com \
    bigquery.googleapis.com \
    --project rentals-data-pipeline
  ```

## Usage

Use the `/terraform` skill — it handles init, fmt, validate, plan, and apply
with confirmation gates:

```bash
/terraform
```

Or run manually:

```bash
# Only on first checkout or after changing the backend block
terraform init

# Standard change loop
terraform plan -out=tfplan.out
terraform apply tfplan.out
```

State locking happens automatically via GCS object generation numbers — concurrent `apply`s on the same prefix are blocked with a clear error.

## Adding more buckets

The bucket's Terraform alias is `scraper-bucket` so additional buckets get
their own non-generic name (`processed-bucket`, `archive-bucket`, etc.)
without renaming this one.

## Adding more Terraform projects

Point a new project's `terraform.tf` at the same backend bucket with a
different prefix:

```hcl
backend "gcs" {
  bucket = "dark-tfstates"
  prefix = "<new-project-name>"
}
```

State for the two projects stays fully isolated.
