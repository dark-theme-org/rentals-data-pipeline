# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Rentals data pipeline. Application code lives in `src/` (src-layout), tests mirror that structure in `tests/`, notebooks in `notebooks/`, operational scripts in `scripts/`, all linter/formatter configs in `.code_quality/`.

Cloud execution is driven by YAML files under `cloud/`:

- **`cloud/tasks/<name>.yml`** — one file per task; defines operator type, entrypoint, Cloud Run machine config, and input parameters with defaults. Terraform reads these to create Cloud Run Jobs; the Docker image reads the matching file at container startup via `scripts/setup_docker.py`.
- **`cloud/workflows/<name>.yml`** — one file per DAG; Cloud Workflows native YAML that sequences tasks into an ordered execution graph. Terraform reads these to create Cloud Workflows.

The `Dockerfile` builds one image per task (`--build-arg TASK_NAME=<name>`). `scripts/setup_docker.py` is the container entrypoint: it reads `cloud/tasks/<TASK_NAME>.yml`, injects parameter defaults, then execs the task command.

## Stack & version pins

- **Python 3.13** — pinned tightly (`>=3.13,<3.14`); see constraints below for why.
- **Poetry 1.8.3** — exact version required by the `/setup` skill.
- **dbt-bigquery 1.11.x** — primary data tool; pulls in dbt-core / dbt-common / dbt-adapters as transitive deps.
- **Quality stack** — `black`, `isort`, `autoflake`, `flake8`, `pylint`, `mypy`, `bandit`, `sqlfluff` (with `sqlfluff-templater-dbt`), `pytest` + cov. All wired through `.pre-commit-config.yaml`.

### Intentional version ceilings — do NOT try to "fix" these

dbt-core's transitive dependencies cap several tools below their latest releases. These are intentional, not bugs:

- **Python 3.13, not 3.14** — dbt-core 1.11 pins `mashumaro <3.15`, and mashumaro 3.14 fails to import on Python 3.14 due to typing-system changes.
- **Black `^25.12.0`** — Black 26+ requires `pathspec >=1.0`; dbt-core requires `<0.13`.
- **mypy `^1.19.0`** — same `pathspec` conflict on mypy 1.20+.

Re-evaluate whenever dbt-core ships a new minor/major.

## Conventions

- **Commit messages** must match `^((analysis|change|feature|fix|refactor|test): .*|Merge .*)$` — enforced by pre-commit's commit-msg hook.
- **Branch prefixes** are independent from commit prefixes: `fix/*`, `enhancement/*`, `feature/*` (lowercase, hyphen-separated, ≤ 3 words).
- **Pre-commit ordering**: `sqlfluff → autoflake → isort → black → flake8 → pylint → mypy → bandit → pytest`. `fail_fast: true` is intentional — surface one problem at a time.
- **Per-contributor files** (gitignored, never commit): `.claude/settings.local.json`, `.python-version`, anything matching `*credentials*.json` / `*service-account*.json`.

See [CODING_GUIDELINES.md](CODING_GUIDELINES.md) for full contributor expectations.

## Claude Code Skills

Custom skills are stored in `.claude/skills/` and enable Claude to assist with project-specific workflows.

### Using Skills

Skills are invoked with the `/skill-name` command:

```bash
/setup                  # Setup local development environment
```

### Skill Structure

Each skill lives in `.claude/skills/<name>/SKILL.md` and uses YAML frontmatter:

```yaml
---
name: Skill name                          # Must match folder name
description: When to invoke this skill    # Recommended action
disable-model-invocation: false           # Allow auto-invocation
user-invocable: true                      # Show in / menu
---

# Skill instructions follow
...
```

**Frontmatter options:**
<!-- markdownlint-disable-line MD058 -->
| Field                       | Purpose                                                     |
|-----------------------------|-------------------------------------------------------------|
| `description`               | When to invoke (used for auto-discovery)                    |
| `disable-model-invocation`  | Set `true` to prevent automatic invocation                  |
| `user-invocable`            | Set `false` to hide from `/` menu (background knowledge)    |
| `allowed-tools`             | Tools allowed without permission prompts (comma-separated)  |
| `model`                     | Model to use when skill is active                           |

### Available Skills

- **`/setup`** — Set up the local development environment for new contributors
  - Detects the required Python version from `pyproject.toml` automatically
  - Checks prerequisites and enforces **Poetry `1.8.3` exactly** (offers `poetry self update 1.8.3` if mismatched)
  - Runs `pyenv install`, then creates `.venv` manually with `$(pyenv which python) -m venv .venv` to bypass a Poetry 1.8.3 system-Python validation bug
  - Clears Poetry caches, runs `poetry install` inside the activated venv, installs and refreshes `pre-commit` hooks, then runs `scripts/setup_local.sh`
  - Validates each step before proceeding; blocking failures stop the flow, non-blocking ones (e.g. `setup_local.sh`) are surfaced but don't abort

- **`/commit`** — Stage, commit, and push the current branch end-to-end with project safety rails
  - Refuses to commit on `develop` / `main` (must be on a `feature/*`, `fix/*`, or `enhancement/*` branch); also aborts if a merge/rebase is in progress
  - Aborts and redirects to `/setup` if `pre-commit` isn't installed or the `pre-commit` / `commit-msg` git hooks aren't wired
  - **Three explicit confirmation gates** — asks the contributor before staging, before committing, and before pushing; every other step (preflight, status surfacing, message drafting, auto-fix retries, post-push report) runs automatically and only pauses to surface a raised issue (security flag, hook failure, divergent remote, etc.)
  - Bundles all pending changes into a single commit; before staging, runs a two-layer security scan — flags risky filenames (`.env`, credentials, `*.key`/`*.pem`, files >500KB) **and** greps diff content for secret markers (PEM headers, cloud credential JSON keys, AWS/Slack/GitHub/GitLab token prefixes, `password=` / `token=` patterns, embedded-credential DB URLs); only after every pending file passes does it stage with `git add -A`, falling back to explicit paths if anything was flagged
  - Drafts a single-line or multi-line commit message based on diff scope and validates the subject against `^((analysis|change|feature|fix|refactor|test): .*|Merge .*)$`
  - Lets pre-commit hooks run (never `--no-verify`); retries up to twice on auto-fix hooks (`black`, `isort`, `autoflake`); on hard failures (`flake8`, `pylint`, `mypy`, `bandit`, `pytest`) leaves staging intact and asks the contributor to fix
  - Fetches and aborts on divergence before pushing (no auto-pull/rebase); never force-pushes

- **`/pr`** — Open a pull request from the current feature branch into a target branch (defaults to `develop` or `main`, but the contributor may override to any branch) with the project's PR template auto-filled
  - Refuses to PR from `develop` / `main` (must be on `feature/*`, `fix/*`, or `enhancement/*`); detects which protected branches (`develop` / `main`) exist on the remote and offers them as named options on the target-branch gate — **the contributor may override to any branch (including a non-protected one) by typing it in the auto-provided `Other` input**
  - Aborts if `gh` is not installed or not authenticated, the remote isn't on GitHub, the branch has no upstream, is ahead of/divergent from the remote, or already has an open PR (surfaces the existing URL)
  - **Two confirmation gates** — asks (1) which target branch to PR into, then (2) whether to open as **draft** or **ready for review**; everything else (preflight, diff analysis, label/assignee resolution, title drafting, template fill, post-create label/assignee application, report) runs automatically
  - Auto-fills the four template sections (`Goal`, reviewer entry points, QA, Other) by analyzing commits and categorized file buckets across `<target>...HEAD`; preserves the template's `* [ ]` checkboxes for reviewers to tick
  - Auto-resolves the **assignee** to the active `gh` login (from `gh api user --jq .login`) and picks **labels** from the repo's existing label set (commit-prefix + file-bucket signals, capped at 3–4); never creates new labels, never assigns anyone else
  - Drafts the PR title in **sentence case with no commit prefix** — leading capital, lowercase rest, identifiers/file paths/slash-commands/acronyms preserved as-is; ~70-char cap, no trailing period (e.g. `Add three confirmation gates to /commit skill`)
  - **Uses the `gh` CLI exclusively** for GitHub API calls — `gh auth status` / `gh api user` for auth, `gh pr list --head` for the duplicate-PR check, `gh label list` for label discovery, `gh pr create --body-file` for creation, then `gh pr edit --add-label --add-assignee` to attach labels/assignees post-create (no GitHub MCP, so per-account auth is just `gh auth switch`)

- **`/pytest`** — Generate clean pytest tests for a Python module under `src/`, mirroring the source layout into `tests/` and reusing or extending the project's shared fixtures
  - **Two `AskUserQuestion` gates only** — at Step 0 the contributor picks the target folder under `src/` (the skill rolls up sibling folders into their common parent, never lists children separately); at the final step it asks **Keep or Rollback**. Everything else (reading source, writing tests, running pytest) runs end-to-end without follow-up questions
  - **Tracks every created and modified path** so the rollback gate can fully undo the run — `created_paths` (test files, new `__init__.py`, conftest if absent) get `rm`'d; `modified_paths` (the cached pre-run content of any pre-existing file edited, typically `tests/conftest.py`) get rewritten verbatim. Unrelated uncommitted work is never touched
  - **Mirrors `src/` into `tests/`** — `src/X/Y/foo.py` → `tests/X/Y/test_foo.py`; creates missing intermediate test subpackages with empty `__init__.py` files; never duplicates the project pytest config (always invokes `.code_quality/pytest.ini`)
  - **All shared fixtures live in the root `tests/conftest.py`**, even when only one test file uses them; uses the `@pytest.fixture(name="x") def x_(...)` pattern (public name + underscored function) to dodge `pylint W0621` without per-line disables; types `mocker: MockerFixture` rather than `# type: ignore`; side-effect-only fixtures are applied via `@pytest.mark.usefixtures("name")` on the test, not as a parameter
  - **Test scope is deliberately narrow** — one success-path test per public method, plus one test per documented `Raises:` clause; skips trivial Python builtins (`KeyError` on dict miss, plain `AttributeError`, dataclass default checks)
  - **Mocks at the import site** (the SUT's module path, e.g. `app.data.scrapers.sites.base.requests.get`), never at the source — patching `requests.get` directly does nothing once the SUT has bound the name at import time; abstract base classes with unset `ClassVar`s are tested via `monkeypatch.setattr(BaseCls, "_VAR", ..., raising=False)` inside a fixture, **never** via a `_StubX` subclass in the test file
  - Verifies via `poetry run pytest -c .code_quality/pytest.ini ...`; if a failure exposes a real bug in `src/`, the skill surfaces it to the contributor and **does not modify `src/` to make the test pass** unless that's clearly the intent

- **`/terraform`** — Manage GCP infrastructure for the rentals data pipeline through the standard Terraform flow defined in [terraform/README.md](terraform/README.md)
  - Aborts if `terraform` CLI isn't installed, the `terraform/` directory is missing, or Application Default Credentials aren't set (`gcloud auth application-default print-access-token` fails); redirects to `gcloud auth application-default login` for the ADC case
  - **Two confirmation gates** — asks (1) the action (apply pending / destroy infrastructure / plan-only), then (2) after seeing the plan summary, whether to apply the saved `tfplan.out`; everything else (preflight, init detection, fmt check, validate, plan generation, post-apply report) runs automatically
  - **Halts on first failure** — every step (init, fmt, validate, plan, apply) is sequential; if any fails the skill surfaces the full error and stops without advancing
  - **Never authors `.tf` files** — the contributor edits infra manually beforehand; the skill is the executor. Auto-runs `terraform fmt` (whitespace-only) only after asking once if `fmt -check` reports drift
  - **Saved plan is the contract** — always runs `terraform plan -out=tfplan.out` (or `-destroy` flavor) and applies that exact saved plan after gate 2; never `terraform apply -auto-approve` against a fresh re-plan
  - **Refuses backend migration / reconfigure** — if `terraform init` would migrate or reconfigure state, the skill stops and tells the contributor to run `terraform init -migrate-state` or `-reconfigure` manually outside the skill
  - **Bootstrap is out of scope** — the skill never runs `gcloud projects create`, `gcloud billing projects link`, `gcloud services enable`, or creates the state bucket; redirects to [terraform/README.md](terraform/README.md) Prerequisites for one-time setup

- **`/run-local`** — Run a pipeline task or workflow locally inside Docker, mirroring the Cloud Run environment
  - **Authorization gate first** — asks the contributor to confirm before doing anything
  - Discovers available targets by reading `cloud/tasks/*.yml` and `cloud/workflows/*.yml`; presents tasks and workflows as options
  - For workflows, extracts the referenced tasks from the workflow YAML and collects parameters from each task file
  - Asks for each input parameter individually, showing the default value and allowing a custom override via **Other**
  - Resolves the SA email from `terraform/locals.tf` + `terraform/iam.tf`; checks Docker is installed and `~/.config/gcloud/darktheme_credentials.json` exists (creates it from the default ADC file if missing)
  - Builds one image per task (`--build-arg TASK_NAME=<name>`) and runs it with `GCS_SA`, `GOOGLE_APPLICATION_CREDENTIALS`, and `GOOGLE_CLOUD_PROJECT` set; for workflows runs tasks sequentially and stops on first failure
  - After the run, asks whether to keep or remove the local image before reporting the outcome

### Creating New Skills

To create a new skill:

1. Create directory: `.claude/skills/<name>/`
2. Create file: `.claude/skills/<name>/SKILL.md` with YAML frontmatter and instructions
3. The skill will be automatically available as `/skill-name`
4. Add documentation here when the skill is ready

---
