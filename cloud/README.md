# cloud/

Central configuration for the GCP cloud execution layer. Every file here
is consumed by at least two of: Terraform, the Docker entrypoint, or the
deploy script — making this the single place to change when adding or
modifying pipeline tasks and workflows.

## Structure

```txt
cloud/
├── settings.yml                      # Project-level GCP config
├── tasks/                            # One YAML file per Cloud Run Job
│   ├── scraper_data_to_bucket.yml
│   ├── gcs_to_bigquery_bronze.yml
│   ├── process_silver_layer.yml
│   └── model_gold_layer.yml
└── workflows/                        # One YAML file per Cloud Workflow
    └── etl_rentals_data.yml
```

---

## `settings.yml`

Single source of truth for GCP project configuration.

```yaml
project_id: rentals-data-pipeline
location: southamerica-east1
developers:
  - user:you@example.com
environments:
  dev: dev
  test: test
  prod: prod
```

**Consumed by:**

- `terraform/locals.tf` — via `yamldecode(file(...))`, drives all resource names and locations; `environments` drives `google_bigquery_dataset` creation; `developers` drives `google_service_account_iam_member.sa_token_creator` grants
- `src/app/utils/utils.py` — `Environment` enum values
- `scripts/deploy.py` — project ID, location, SA email, and Artifact Registry URL

> **Note:** the `prefix` in `terraform/terraform.tf`'s backend block must be kept in
> sync manually — Terraform backend blocks cannot use `locals` or `file()`.

---

## `tasks/<name>.yml`

Defines a single Cloud Run Job. The filename (without `.yml`) is the task name
and is used as-is across Docker builds, Terraform resources, and env vars.

**Schema:**

```yaml
description: <human-readable description>
type: python | dbt         # operator type; drives the exec command in setup_docker.py
machine:
  cpu: "1"                 # vCPU allocation
  memory: 512Mi            # memory limit
  timeout: 600s            # max execution time
retry:
  repetitions: 0           # Cloud Run Job max-retries
entrypoint: <value>        # python: dotted module path; dbt: sub-command + flags string
inputs:
  parameters:
    - name: PARAM_NAME     # uppercase by convention (env var name)
      default: value       # used when not overridden at runtime
```

> **Note:** `PROJECT_ID` and `LOCATION` are never declared as task parameters.
> `scripts/setup_docker.py` injects them automatically from `cloud/settings.yml`
> after the task parameters are set, so every task has them available as env vars.

**Consumed by:**

- `Dockerfile` + `scripts/setup_docker.py` — one image per task; entrypoint reads this file at container startup to inject parameter defaults
- `terraform/` *(future)* — Terraform `yamldecode` loop creates one Cloud Run Job per file
- `scripts/deploy.py` — `build_and_push_images` and `deploy_task` read machine config and parameters

**Adding a new task:** drop a new `.yml` file in this folder. The Docker build,
Terraform, and deploy script all pick it up automatically.

---

## `workflows/<name>.yml`

Defines a single Cloud Workflow in [Cloud Workflows native YAML syntax](https://cloud.google.com/workflows/docs/reference/syntax).
Each step calls one or more Cloud Run Jobs in sequence.

**Key patterns used:**

```yaml
# project_id and location come from workflow args, not from Cloud Workflows sys env vars.
# scripts/deploy.py reads cloud/settings.yml and injects them into the --data payload.
- project_id: ${map.get(args, "PROJECT_ID")}
- location:   ${map.get(args, "LOCATION")}

# Accept runtime arguments (keys must be UPPERCASE to match Cloud Run env var convention)
- ENVIRONMENT: ${map.get(args, "ENVIRONMENT")}

# Trigger a Cloud Run Job
call: googleapis.run.v2.projects.locations.jobs.run
args:
  name: ${"projects/" + project_id + "/locations/" + location + "/jobs/<job-name>"}
  body:
    overrides:
      containerOverrides:
        - env:
            - name: PARAM_NAME
              value: ${param_value}
```

> **Note:** `PROJECT_ID` and `LOCATION` are **not** passed as `containerOverrides` env vars.
> `scripts/setup_docker.py` injects them into every container at startup from `cloud/settings.yml`,
> so the workflow only needs them to construct the Cloud Run job resource path.

**Consumed by:**

- `scripts/deploy.py` — `deploy_workflow` uploads this file via `gcloud workflows deploy`; `run_workflow` triggers execution via `gcloud workflows run`
- `terraform/` *(future)* — Terraform `fileset` loop creates one Cloud Workflow per file

**Adding a new workflow:** drop a new `.yml` file in this folder following the
Cloud Workflows syntax. The deploy script picks it up automatically.

---

## Pipeline overview — `etl_rentals_data`

The workflow sequences four Cloud Run Jobs in order:

| Step | Job | Key inputs |
| --- | --- | --- |
| 1 | `scraper-data-to-bucket` | ENVIRONMENT, CITY, SITES, PROPERTY_TYPES, UPLOAD_TO_GCS, START_PAGE, MAX_PAGE |
| 2 | `gcs-to-bigquery-bronze` | ENVIRONMENT, CITY, SITES, PROPERTY_TYPES, FILE_DATE, UPLOAD_TO_BQ, START_PAGE, MAX_PAGE |
| 3 | `process-silver-layer` | ENVIRONMENT, CITY, SITES, PROPERTY_TYPES, FILE_DATE |
| 4 | `model-gold-layer` | ENVIRONMENT, FILE_DATE |

`FILE_DATE` (format `YYYY-MM-DD`) controls which scrape date is loaded by steps 2–4.
Leave it empty to default to `CURRENT_DATE`.

---

## Triggering a workflow manually

```bash
# Replace 0-0-1 with the version tag used when the workflow was deployed
gcloud workflows run etl-rentals-data-0-0-1 \
  --location southamerica-east1 \
  --project rentals-data-pipeline \
  --data='{"PROJECT_ID":"rentals-data-pipeline","LOCATION":"southamerica-east1","VERSION":"0-0-1","ENVIRONMENT":"dev","CITY":"macae","SITES":"vivareal","PROPERTY_TYPES":"apartment","UPLOAD_TO_GCS":"true","START_PAGE":"1","MAX_PAGE":"-1","FILE_DATE":"","UPLOAD_TO_BQ":"true"}'
```

The workflow name must match the versioned name created by `deploy.py`
(`<workflow-name>-<version>`, dots replaced by dashes). All data arguments are
optional when the workflow uses `default()` — argument keys must be **uppercase**
to match the Cloud Run env var convention.
