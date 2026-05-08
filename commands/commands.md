# commands

Operational shell scripts that support onboarding, local development, and
routine maintenance. This folder is intentionally separate from `src/`
(application code) and `tests/` (test code) — its scripts run *around* the
project rather than inside it.

## When to put a script here

- Onboarding flows that prepare a contributor's machine (install tools,
  bootstrap dependencies).
- One-off maintenance tasks invoked manually (cache cleanup, lockfile
  refresh, environment reset).
- Glue scripts called by the `.claude/skills/` workflows.

If a task is part of the application's runtime behavior, it belongs in
`src/`. If it is a Python utility used by tests or notebooks, it belongs
in those folders, not here.

## Conventions

- **Shebang** — start every script with `#!/bin/bash`. The scripts in this
  folder use bash-specific syntax (`function name() {}`, `&>/dev/null`,
  `[[ ... ]]`), which `dash` (the default `/bin/sh` on most Linux distros)
  does not parse. Always invoke with `bash`, not `sh`.
- **Working directory** — scripts assume they are run from the project
  root, e.g. `bash commands/setup_local.sh`. Use relative paths
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
    `bash commands/setup_local.sh`.
