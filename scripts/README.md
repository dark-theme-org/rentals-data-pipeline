# scripts/

Operational scripts that support onboarding, local development, and the
cloud execution layer. This folder is intentionally separate from `src/`
(application code) and `tests/` (test code) — its scripts run *around* the
project rather than inside it.

## When to put a script here

- Onboarding flows that prepare a contributor's machine (install tools, bootstrap dependencies).
- One-off maintenance tasks invoked manually (cache cleanup, lockfile refresh, environment reset).
- Glue scripts called by the `.claude/skills/` workflows.
- Docker runtime scripts that support container execution.
- Deployment scripts that push images and provision cloud resources.

If a task is part of the application's runtime behavior, it belongs in
`src/`. If it is a Python utility used by tests or notebooks, it belongs
in those folders, not here.

## Conventions

- **Shebang** — start every shell script with `#!/bin/bash`. The scripts in
  this folder use bash-specific syntax (`function name() {}`, `&>/dev/null`,
  `[[ ... ]]`), which `dash` (the default `/bin/sh` on most Linux distros)
  does not parse. Always invoke with `bash`, not `sh`.
- **Working directory** — scripts assume they are run from the project
  root, e.g. `bash scripts/setup_local.sh`. Use relative paths
  (`.code_quality/...`, `.venv/bin/...`) accordingly.
- **Logging prefix** — emit messages with `LOG::[INFO]` or `LOG::[ERROR]`
  prefixes so output is easy to grep when surfaced through CI logs or the
  `/setup` skill.
- **Idempotency** — scripts must be safe to re-run. Check for existing
  state (e.g. `command -v claude` before installing) instead of assuming a
  clean machine.
- **Failure mode** — for optional steps, surface errors via `LOG::[ERROR]`
  and continue rather than aborting the parent process. The contributor
  should see what failed without losing the rest of the run.

## Available scripts

- **`setup_local.sh`** — Installs the Claude CLI (if missing) and the
  `local` Poetry dependency group used by notebooks (matplotlib, seaborn,
  ipykernel, etc.).
  - *Invocation*: run automatically by the `/setup` skill at the end of
    the onboarding flow; can also be invoked directly with
    `bash scripts/setup_local.sh`.

- **`setup_docker.py`** — Docker container entry point. Reads
  `cloud/tasks/<TASK_NAME>.yml` at startup, validates the task type,
  injects parameter defaults for any env vars not already set, then execs
  the task command (replacing itself so exit codes and signals propagate
  cleanly to Cloud Run).
  - *Invocation*: called automatically by the Docker container via `CMD`;
    never invoked directly. Requires `TASK_NAME` to be set as an env var
    (baked in at image build time via `--build-arg TASK_NAME=<name>`).

- **`deploy.py`** — Manages the full deployment cycle: builds and pushes
  Docker images, creates versioned Cloud Run Jobs, deploys Cloud Workflow
  definitions, and triggers workflow executions. Reads project config from
  `cloud/settings.yml`.

  The `--version` tag is appended to all GCP resource names so multiple
  versions can coexist:
  - Image: `scraper_data_to_bucket:0.0.1`
  - Cloud Run Job: `scraper-data-to-bucket-0-0-1`
  - Cloud Workflow: `etl-rentals-data-0-0-1`

  - *Invocation*: `poetry run python scripts/deploy.py --version <tag>`
  - *Prerequisites (one-time setup per machine)*:

    ```bash
    # Authenticate gcloud
    gcloud auth login

    # Configure Docker to use gcloud credentials for Artifact Registry
    gcloud auth configure-docker us-central1-docker.pkg.dev
    ```

  - *Flags*:

    | Flag | Effect |
    | --- | --- |
    | `--version` | *(required)* Docker image tag; appended to all GCP resource names |
    | `--tasks` | Build/deploy only the named task(s). All if omitted |
    | `--workflow` | Deploy/run only the named workflow. All if omitted |
    | `--params` | Override parameter values, e.g. `ENVIRONMENT=prod CITY=rio` |
    | `--skip-build` | Skip `docker build` and `docker push` |
    | `--skip-task-deploy` | Skip Cloud Run Job creation |
    | `--skip-workflow-deploy` | Skip Cloud Workflow definition upload |
    | `--skip-workflow-run` | Skip Cloud Workflow execution trigger |

  - *Common usage*:

    ```bash
    # Full cycle — build, deploy job, deploy workflow, trigger execution
    poetry run python scripts/deploy.py --version 0.0.1 \
      --params ENVIRONMENT=dev CITY=macae SITES=vivareal PROPERTY_TYPES=apartment,house

    # Build and push images only
    poetry run python scripts/deploy.py --version 0.0.1 \
      --skip-task-deploy --skip-workflow-deploy --skip-workflow-run

    # Trigger workflow execution only (job and workflow already deployed)
    poetry run python scripts/deploy.py --version 0.0.1 \
      --skip-build --skip-task-deploy --skip-workflow-deploy \
      --params ENVIRONMENT=prod CITY=macae SITES=vivareal PROPERTY_TYPES=apartment,house

    # Deploy and run a specific workflow
    poetry run python scripts/deploy.py --version 0.0.1 \
      --skip-build --skip-task-deploy --workflow etl_rentals_data \
      --params ENVIRONMENT=dev CITY=macae SITES=vivareal PROPERTY_TYPES=apartment,house
    ```
