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

- **`deploy.py`** — Deploys Cloud Run Jobs and Cloud Workflows from
  `cloud/tasks/` and `cloud/workflows/` YAML definitions. Reads project
  config from `cloud/settings.yml`.
  - *Invocation*: `poetry run python scripts/deploy.py --version <tag>`
  - *Prerequisites (one-time setup per machine)*:

    ```bash
    # Authenticate gcloud
    gcloud auth login

    # Configure Docker to use gcloud credentials for Artifact Registry
    gcloud auth configure-docker us-central1-docker.pkg.dev
    ```

  - *Common usage*:

    ```bash
    # Full deploy — build images, create Cloud Run Jobs, deploy Workflows
    poetry run python scripts/deploy.py --version 0.0.1

    # Build and push images only
    poetry run python scripts/deploy.py --version 0.0.1 --skip-deploy --skip-run

    # Deploy a specific task only
    poetry run python scripts/deploy.py --version 0.0.1 --tasks scraper_data_to_bucket

    # Override task parameters at deploy time
    poetry run python scripts/deploy.py --version 0.0.1 --params ENVIRONMENT=prod CITY=rio

    # Deploy a specific workflow only
    poetry run python scripts/deploy.py --version 0.0.1 --skip-build --skip-deploy --workflow etl_rentals_data
    ```
