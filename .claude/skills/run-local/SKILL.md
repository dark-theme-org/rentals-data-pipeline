---
name: run-local
description: Run a pipeline task or workflow locally inside Docker, mirroring the Cloud Run environment with ADC impersonation.
user-invocable: true
allowed-tools: Bash, Read, AskUserQuestion
---

# Run Local Skill

Runs a pipeline task or workflow locally in Docker with the same environment as Cloud Run —
ADC credentials mounted, SA impersonation via `GCS_SA`, and the correct `TASK_NAME` baked
into the image at build time.

---

## Step 0 — Authorization gate

Before doing anything else, ask the user to explicitly authorize the skill run.
Do not read files, run commands, or proceed in any way until confirmed.

Use `AskUserQuestion`:

- **question**: `"This will build and run a Docker image locally. Proceed?"`
- **header**: `"Authorization"`
- **options**:
  - `"Yes, proceed"` — continue to Step 1
  - `"Cancel"` — stop immediately with no further action
- **multiSelect**: `false`

If the user selects **Cancel**, exit cleanly with the message:
> Run cancelled. Invoke `/run-local` again whenever you are ready.

---

## Step 1 — Discover available tasks and workflows

Read every task file under `cloud/tasks/` and every workflow file under `cloud/workflows/`.
For each file, parse the YAML to extract the `description` field.

```bash
find cloud/tasks -name "*.yml" | sort
find cloud/workflows -name "*.yml" | sort
```

---

## Step 2 — Question 1: What do you want to run?

Use `AskUserQuestion` with one question:

- **question**: `"What do you want to run?"`
- **header**: `"Target"`
- **options**: one entry per task and workflow discovered. Prefix tasks with `Task:` and
  workflows with `Workflow:`. Use the `description` from the YAML as the option description.
- **multiSelect**: `false`

---

## Step 3 — Determine parameters for the selected target

**If a task was selected:**
- Read `cloud/tasks/<task_name>.yml`
- Extract `inputs.parameters` → list of `{ name, default }` entries

**If a workflow was selected:**
- Read `cloud/workflows/<workflow_name>.yml`
- Scan for lines containing `/jobs/` to extract Cloud Run Job names
  (e.g. `/jobs/scraper-data-to-bucket`)
- Convert each job name to a task name by replacing `-` with `_`
  (e.g. `scraper-data-to-bucket` → `scraper_data_to_bucket`)
- For each resolved task name, read `cloud/tasks/<task_name>.yml` and collect
  `inputs.parameters`
- Deduplicate parameters by `name` — same parameter across multiple tasks appears once

---

## Step 4 — Question 2: Input parameters

Use `AskUserQuestion` with one question per parameter (up to 4 questions per call;
make multiple calls if there are more than 4 parameters). For each parameter:

- **question**: `"Value for <PARAM_NAME>?"`
- **header**: `<PARAM_NAME>`
- **options**: single option — `label: "<default_value>"`, `description: "Default value"`.
  The automatic **Other** option lets the user type a custom value.
- **multiSelect**: `false`

Collect all answers before proceeding.

---

## Step 5 — Resolve the SA email

Read `terraform/locals.tf` to extract `project_id`.
Read `terraform/iam.tf` to extract the `account_id` of `google_service_account.sa`.
Construct the email as: `<account_id>@<project_id>.iam.gserviceaccount.com`

---

## Step 6 — Check prerequisites

Run both checks and stop with a clear message if either fails:

```bash
# Docker installed
docker --version

# Project-specific ADC credentials exist
ls ~/.config/gcloud/darktheme_credentials.json
```

If `darktheme_credentials.json` is missing:
1. Run `gcloud auth application-default login` to refresh the default ADC file
2. Copy it to the project-specific location:
   ```bash
   cp ~/.config/gcloud/application_default_credentials.json \
      ~/.config/gcloud/darktheme_credentials.json
   ```
3. Confirm the file now exists before continuing.

---

## Step 7 — Build the Docker image

For the selected task (or each task in a workflow, in declaration order):

```bash
docker build \
  --build-arg TASK_NAME=<task_name> \
  -t <task_name>:local \
  .
```

Show build output so the user can follow progress.

---

## Step 8 — Run

**Single task:**

```bash
docker run --rm \
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json \
  -v ~/.config/gcloud/darktheme_credentials.json:/tmp/adc.json:ro \
  -e GCS_SA=<sa_email> \
  -e <PARAM_NAME>=<value> \
  ... \
  <task_name>:local
```

**Workflow:** run each task in sequence using the same pattern. If any task exits with a
non-zero code, stop and surface the error — do not continue to the next task.

---

## Step 9 — Cleanup

After the run completes (success or failure), ask the user whether to keep or remove the local image:

- **question**: `"Keep or remove the local Docker image?"`
- **header**: `"Image cleanup"`
- **options**:
  - `"Remove"` — delete the image to free disk space (`docker rmi <task_name>:local`)
  - `"Keep"` — leave the image locally for faster re-runs without rebuilding
- **multiSelect**: `false`

Apply the user's choice, then report the outcome: success with a summary of what ran and the
final image state, or the Docker error output if the run failed.
