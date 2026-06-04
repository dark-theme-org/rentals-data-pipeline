---
name: cloud-deploy
description: Deploy Cloud Run Jobs and Cloud Workflows from cloud/ YAML definitions by guiding the user through scripts/deploy.py arguments.
user-invocable: true
allowed-tools: Bash, Read, AskUserQuestion
---

# Cloud Deploy Skill

Guides the contributor through a full or partial deployment by interactively
collecting every argument for `scripts/deploy.py`, validating prerequisites,
showing the exact command before executing, and reporting the outcome.

---

## Step 0 — Authorization gate

Before doing anything else, ask the user to explicitly authorize the skill run.
Do not read files, run commands, or proceed in any way until confirmed.

Use `AskUserQuestion`:

- **question**: `"This will build and/or deploy to GCP. Proceed?"`
- **header**: `"Authorization"`
- **options**:
  - `"Yes, proceed"` — continue to Step 1
  - `"Cancel"` — stop immediately with no further action
- **multiSelect**: `false`

If the user selects **Cancel**, exit cleanly with the message:
> Deployment cancelled. Invoke `/cloud-deploy` again whenever you are ready.

---

## Step 1 — Prerequisites

Run both checks and stop with a clear message if either fails:

```bash
docker --version
docker buildx version
```

If Docker is missing: tell the contributor to install Docker Desktop and stop.

If buildx is missing:
> `docker buildx` is required for cross-platform builds. Install it with:
> ```bash
> brew install docker-buildx
> mkdir -p ~/.docker/cli-plugins
> ln -sf /opt/homebrew/opt/docker-buildx/bin/docker-buildx ~/.docker/cli-plugins/docker-buildx
> ```
> Then re-run `/cloud-deploy`.

---

## Step 2 — Discover available tasks and workflows

Read every task file under `cloud/tasks/` and every workflow file under
`cloud/workflows/`. For each file, parse the YAML to extract `description`
and `inputs.parameters` (with `name` and `default` for each parameter).

```bash
find cloud/tasks -name "*.yml" | sort
find cloud/workflows -name "*.yml" | sort
```

Also read `cloud/settings.yml` to resolve `project_id` and `location`.

---

## Step 3 — Version

Ask for the Docker image tag that will be used for the image name, Cloud Run
Job name, and Cloud Workflow name (all three are versioned with this value).

Use `AskUserQuestion`:

- **question**: `"What version tag should be used?"`
- **header**: `"--version"`
- **options**:
  - `"dev"` — development build
  - `"0.0.1"` — suggested semantic version
- **multiSelect**: `false`

The **Other** option lets the contributor type any custom version string.
Record as `<version>`.

---

## Step 4 — Tasks

Ask which tasks to include in the build/deploy steps.

Use `AskUserQuestion`:

- **question**: `"Which tasks should be included?"`
- **header**: `"--tasks"`
- **options**:
  - `"All tasks"` — omit `--tasks` (default behaviour)
  - One option per discovered task file: `label: "<task_stem>"`, `description: "<task description>"`
- **multiSelect**: `false`

Record as `<selected_tasks>` (empty = all).

---

## Step 5 — Build and task-deploy skip flags

Ask two boolean questions in one `AskUserQuestion` call:

- **question 1**: `"Skip docker buildx build + push?"`
  - **header**: `"--skip-build"`
  - **options**: `"No — build and push the image"` / `"Yes — skip build"`
- **question 2**: `"Skip Cloud Run Job creation?"`
  - **header**: `"--skip-task-deploy"`
  - **options**: `"No — create the Cloud Run Job"` / `"Yes — skip job creation"`

Record `skip_build` and `skip_task_deploy` booleans.

---

## Step 6 — Parameters

Collect parameter overrides for `--params`. Use the parameters from each
selected task's `inputs.parameters` list (deduplicated by name). For each
parameter ask one question (up to 4 per `AskUserQuestion` call; make multiple
calls if needed):

- **question**: `"Value for <PARAM_NAME>?"`
- **header**: `<PARAM_NAME>`
- **options**: `label: "<default>"`, `description: "Default value"` plus one
  meaningful alternative (e.g. `"prod"` for `ENVIRONMENT`).
- **multiSelect**: `false`

The **Other** option lets the contributor type a custom value. Only include
`--params` in the command if at least one value differs from the task YAML default.

---

## Step 7 — Workflow

Ask which workflow to target.

Use `AskUserQuestion`:

- **question**: `"Which workflow should be deployed/run?"`
- **header**: `"--workflow"`
- **options**:
  - `"All workflows"` — omit `--workflow` (default behaviour)
  - One option per discovered workflow file: `label: "<workflow_stem>"`,
    `description: "<workflow description from the YAML comment>"`
- **multiSelect**: `false`

Record as `<selected_workflow>` (empty = all).

---

## Step 8 — Workflow skip flags

Ask two boolean questions in one `AskUserQuestion` call:

- **question 1**: `"Skip Cloud Workflow definition upload?"`
  - **header**: `"--skip-workflow-deploy"`
  - **options**: `"No — upload workflow definition"` / `"Yes — skip workflow deploy"`
- **question 2**: `"Skip Cloud Workflow execution trigger?"`
  - **header**: `"--skip-workflow-run"`
  - **options**: `"No — trigger workflow execution"` / `"Yes — skip workflow run"`

Record `skip_workflow_deploy` and `skip_workflow_run` booleans.

---

## Step 9 — Show command and confirm

Construct the full `scripts/deploy.py` command from all collected answers:

```
poetry run python scripts/deploy.py \
  --version <version> \
  [--tasks <task1> <task2> ...] \
  [--skip-build] \
  [--skip-task-deploy] \
  [--params <KEY=VALUE> ...] \
  [--workflow <workflow>] \
  [--skip-workflow-deploy] \
  [--skip-workflow-run]
```

Show the exact command to the contributor, then use `AskUserQuestion`:

- **question**: `"Run this command?"`
- **header**: `"Confirm"`
- **options**:
  - `"Run"` — execute the command
  - `"Cancel"` — stop without running
- **multiSelect**: `false`

If **Cancel**, exit cleanly.

---

## Step 10 — Execute

Run the constructed command from the project root:

```bash
poetry run python scripts/deploy.py <args...>
```

Stream output to the contributor so they can follow progress. The script
already prints step labels (`[build:...]`, `[deploy:...]`, `[run-workflow:...]`)
and exits with code 1 on any failure.

---

## Step 11 — Report outcome

**On success:** print a summary of what ran:
- Version deployed
- Tasks built/deployed (or skipped)
- Workflows deployed/triggered (or skipped)
- GCP resource names created (derived from version + task/workflow names)

**On failure:** surface the full error output from the script (the
`ERROR [step]:` line and the gcloud/docker stderr) so the contributor
knows exactly which step failed and why.
