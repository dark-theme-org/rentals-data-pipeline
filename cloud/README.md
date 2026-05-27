# cloud/

Central configuration for the GCP cloud execution layer. Every file here
is consumed by at least two of: Terraform, the Docker entrypoint, or the
deploy script — making this the single place to change when adding or
modifying pipeline tasks and workflows.

## Structure

```txt
cloud/
├── settings.yml        # Project-level GCP config (project_id, region)
├── tasks/              # One YAML file per Cloud Run Job
│   └── <task_name>.yml
└── workflows/          # One YAML file per Cloud Workflow
    └── <workflow_name>.yml
```

---

## `settings.yml`

Single source of truth for GCP project configuration.

```yaml
project_id: rentals-data-pipeline
region: southamerica-east1
developers:
  - user:you@example.com
environments:
  dev: dev
  test: test
  prod: prod
```

**Consumed by:**

- `terraform/locals.tf` — via `yamldecode(file(...))`, drives all resource names and locations; `environments` drives `google_bigquery_dataset` creation; `developers` drives `google_service_account_iam_member.sa_token_creator` grants
- `src/app/utils/utils.py` — `CloudSettings.PROJECT_ID`, `CloudSettings.REGION`, and `Environment` enum values
- `scripts/deploy.py` — project ID, region, SA email, and Artifact Registry URL

> **Note:** the `prefix` in `terraform/terraform.tf`'s backend block must be kept in
> sync manually — Terraform backend blocks cannot use `locals` or `file()`.

---

## `tasks/<name>.yml`

Defines a single Cloud Run Job. The filename (without `.yml`) is the task name
and is used as-is across Docker builds, Terraform resources, and env vars.

**Schema:**

```yaml
description: <human-readable description>
type: python               # operator type; drives the exec command
machine:
  cpu: "1"                 # vCPU allocation
  memory: 512Mi            # memory limit
  timeout: 600s            # max execution time
retry:
  repetitions: 0           # Cloud Run Job max-retries
entrypoint: <module.path>  # Python module path
inputs:
  parameters:
    - name: PARAM_NAME     # uppercase by convention (env var name)
      default: value       # used when not overridden at runtime
```

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
# Read project and location from the Cloud Workflows runtime
- project_id: ${sys.get_env("GOOGLE_CLOUD_PROJECT_ID")}
- location:   ${sys.get_env("GOOGLE_CLOUD_LOCATION")}

# Accept runtime arguments (keys must be UPPERCASE to match Cloud Run env var convention)
# Wrap with default() to provide a fallback when the arg is omitted at runtime
- ENVIRONMENT: ${default(map.get(args, "ENVIRONMENT"), "dev")}

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

**Consumed by:**

- `scripts/deploy.py` — `deploy_workflow` uploads this file via `gcloud workflows deploy`; `run_workflow` triggers execution via `gcloud workflows run`
- `terraform/` *(future)* — Terraform `fileset` loop creates one Cloud Workflow per file

**Adding a new workflow:** drop a new `.yml` file in this folder following the
Cloud Workflows syntax. The deploy script picks it up automatically.

---

## Triggering a workflow manually

```bash
# Replace 0-0-1 with the version tag used when the workflow was deployed
gcloud workflows run etl-rentals-data-0-0-1 \
  --location southamerica-east1 \
  --project rentals-data-pipeline \
  --data='{"VERSION":"0-0-1","ENVIRONMENT":"dev","CITY":"macae","SITES":"vivareal","PROPERTY_TYPES":"apartment","UPLOAD_TO_GCS":"true","START_PAGE":"1","MAX_PAGE":"-1","FILE_DATE":"","UPLOAD_TO_BQ":"true"}'
```

The workflow name must match the versioned name created by `deploy.py`
(`<workflow-name>-<version>`, dots replaced by dashes). All data arguments are
optional when the workflow uses `default()` — argument keys must be **uppercase**
to match the Cloud Run env var convention.
