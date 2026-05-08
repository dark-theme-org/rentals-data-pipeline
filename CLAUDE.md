# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Rentals data pipeline. Application code lives in `src/` (src-layout), tests mirror that structure in `tests/`, notebooks in `notebooks/`, operational shell scripts in `commands/`, all linter/formatter configs in `.code_quality/`.

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
  - Clears Poetry caches, runs `poetry install` inside the activated venv, installs and refreshes `pre-commit` hooks, then runs `commands/setup_local.sh`
  - Validates each step before proceeding; blocking failures stop the flow, non-blocking ones (e.g. `setup_local.sh`) are surfaced but don't abort

- **`/commit`** — Stage, commit, and push the current branch end-to-end with project safety rails
  - Refuses to commit on `develop` / `master` / `main` (must be on a `feature/*`, `fix/*`, or `enhancement/*` branch); also aborts if a merge/rebase is in progress
  - Aborts and redirects to `/setup` if `pre-commit` isn't installed or the `pre-commit` / `commit-msg` git hooks aren't wired
  - Bundles all pending changes into a single commit; before staging, runs a two-layer security scan — flags risky filenames (`.env`, credentials, `*.key`/`*.pem`, files >500KB) **and** greps diff content for secret markers (PEM headers, cloud credential JSON keys, AWS/Slack/GitHub/GitLab token prefixes, `password=` / `token=` patterns, embedded-credential DB URLs); only after every pending file passes does it stage with `git add -A`, falling back to explicit paths if anything was flagged
  - Drafts a single-line or multi-line commit message based on diff scope and validates the subject against `^((analysis|change|feature|fix|refactor|test): .*|Merge .*)$`
  - Lets pre-commit hooks run (never `--no-verify`); retries up to twice on auto-fix hooks (`black`, `isort`, `autoflake`); on hard failures (`flake8`, `pylint`, `mypy`, `bandit`, `pytest`) leaves staging intact and asks the contributor to fix
  - Confirms before pushing; fetches and aborts on divergence (no auto-pull/rebase); never force-pushes

### Creating New Skills

To create a new skill:

1. Create directory: `.claude/skills/<name>/`
2. Create file: `.claude/skills/<name>/SKILL.md` with YAML frontmatter and instructions
3. The skill will be automatically available as `/skill-name`
4. Add documentation here when the skill is ready

---
