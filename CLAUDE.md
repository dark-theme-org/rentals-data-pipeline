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
  - Checks prerequisites (`pyenv`, `poetry`) and guides installation if missing
  - Runs `pyenv install`, `poetry install`, sets up `pre-commit` hooks, runs `commands/setup_local.sh`, and finally `poetry shell`
  - Validates each step before proceeding and surfaces errors clearly

- **`/commit`** — Stage, commit, and push the current branch end-to-end with project safety rails
  - Refuses to commit on `develop` / `master` / `main` (must be on a `feature/*`, `fix/*`, or `enhancement/*` branch)
  - Stages files by explicit path (never `git add -A` / `.`); flags risky patterns (`.env`, credentials, large files) for explicit opt-in
  - Drafts a commit message from the staged diff and validates it against the project's commit-msg regex
  - Lets pre-commit hooks run (never bypasses them); handles auto-fix retries and hard failures cleanly
  - Confirms with the contributor before pushing; never force-pushes; never auto-resolves a divergent push

### Creating New Skills

To create a new skill:

1. Create directory: `.claude/skills/<name>/`
2. Create file: `.claude/skills/<name>/SKILL.md` with YAML frontmatter and instructions
3. The skill will be automatically available as `/skill-name`
4. Add documentation here when the skill is ready

---
