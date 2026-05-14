# Terraform

GCP infrastructure for the **Rentals Data Pipeline** project. Manages the GCS bucket where scraped rentals data lands and the service account the pipeline runs as. Remote state is stored in a shared GCS backend (`dark-tfstates`) hosted in the dedicated `darktheme-ops` project, so future Terraform projects can share the same bucket under their own prefix.

## What this stack creates

| Resource | What it is |
| --- | --- |
| `google_storage_bucket.scraper-bucket` | `scraper-rentals-data` bucket. Regional in `us-central1`, UBLA on, public access blocked, versioning on, soft-delete 7 days, lifecycle deletes live objects after 30 days, caps noncurrent versions at 5 |
| `google_service_account.gcs_sa` | `${project_id}-gcs-sa` — the runner identity used by Cloud Run Jobs to read and write to GCS |
| `google_service_account.workflows_sa` | `${project_id}-workflows-sa` — the identity used by Cloud Workflows to trigger Cloud Run Jobs |
| `google_storage_bucket_iam_member.gcs_sa` | Bucket-scoped binding granting `gcs_sa` `roles/storage.objectAdmin` on the data bucket only |

## Files

| File | Purpose |
| --- | --- |
| [terraform.tf](terraform.tf) | `terraform {}` meta block — required CLI/provider versions, and the `backend "gcs"` block pointing at `gs://dark-tfstates/rentals-data-pipeline/state/`. Also configures the `google` provider (project + default region from variables) |
| [variables.tf](variables.tf) | Input variables. Currently `project_id` (default `rentals-data-pipeline`) and `region` (default `us-central1`). Override via `terraform.tfvars`, `-var`, or `TF_VAR_*` env vars |
| [gcs.tf](gcs.tf) | The data bucket and all of its bucket-level settings (storage class, labels, versioning, soft-delete policy, lifecycle rules) |
| [iam.tf](iam.tf) | The pipeline service account (`account_id` derived as `${var.project_id}-sa`) and the bucket-scoped IAM binding for `roles/storage.objectAdmin` |

## Prerequisites

- `gcloud` and `terraform >= 1.6` installed
- Application Default Credentials set: `gcloud auth application-default login` — must be the Google account with access to both `darktheme-ops` (state) and `rentals-data-pipeline` (resources)
- The `darktheme-ops` project and `gs://dark-tfstates` state bucket exist (already bootstrapped — see commit history)
- The `rentals-data-pipeline` project exists with billing linked and the `storage.googleapis.com` + `iam.googleapis.com` APIs enabled

## Usage

```bash
cd terraform/

# Only on first checkout (or when changing the backend block)
terraform init

# Validate that the .tf files parse and are internally consistent
# (resource references resolve, no missing required arguments, etc.).
# Fast and offline — does not contact GCP.
terraform validate

# Standard change loop
terraform plan -out=tfplan.out
terraform apply tfplan.out
```

State locking happens automatically via GCS object generation numbers — concurrent `apply`s on the same prefix are blocked with a clear error.

## Adding more buckets later

The bucket's Terraform alias is `scraper-bucket` (not `bucket`) so additional buckets in this stack get their own non-generic name (`processed-bucket`, `archive-bucket`, etc.) without renaming this one.

## Adding more Terraform projects later

Point a new project's `terraform.tf` at the same backend bucket with a different prefix:

```hcl
backend "gcs" {
  bucket = "dark-tfstates"
  prefix = "<new-project-name>"
}
```

State for the two projects stays fully isolated.
