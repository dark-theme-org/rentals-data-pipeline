---
name: setup
description: Set up the local development environment for new contributors — installs Python via pyenv, configures Poetry, sets up pre-commit hooks, and runs setup_local.sh
user-invocable: true
allowed-tools: Bash, Read, Glob
---

# Dev Environment Setup Skill

Your task is to guide a new contributor through setting up the local development environment for this project, step by step. Execute each step, validate it succeeded, and only move forward when it's safe to do so.

## Language

Interact with the user in the same language they used to invoke the skill.

## Overview of Steps

1. Detect required Python version from `pyproject.toml`
2. Check prerequisites (`pyenv`, `poetry`) and ensure Poetry is version `1.8.3`
3. Install and activate the correct Python version via `pyenv`
4. Configure Poetry to use that Python
5. Clear Poetry caches
6. Install dependencies via `poetry install`
7. Set up pre-commit hooks
8. Run `commands/setup_local.sh`

---

## Step-by-Step Instructions

### Step 0 — Read the required Python version

Read `pyproject.toml` and extract the Python version constraint under `[tool.poetry.dependencies]`. The field looks like:

```toml
python = ">=3.13,<3.14"
```

Extract the **install target** as the lower bound major.minor (e.g. `3.13`). Use this version for all subsequent steps.

---

### Step 1 — Check prerequisites

Run these checks sequentially. If a prerequisite is missing, stop and give the contributor clear installation instructions before continuing.

```bash
# Check pyenv
command -v pyenv

# Check poetry
command -v poetry
```

**If `pyenv` is missing:**
Tell the contributor to install it:
- macOS: `brew install pyenv` then add to shell profile:
  ```bash
  echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
  echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
  echo 'eval "$(pyenv init -)"' >> ~/.zshrc
  source ~/.zshrc
  ```

- Linux: `curl https://pyenv.run | bash` then follow the same profile steps

**If poetry is missing:**
Tell the contributor to install it:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```


Do not continue until the contributor confirms prerequisites are in place.

**Check Poetry version:**

```bash
poetry --version
```

This project requires *Poetry 1.8.3* exactly. If the installed version differs, update it:

```bash
poetry self update 1.8.3
```

Validate again with `poetry --version` and confirm it shows `1.8.3` before continuing.

---

### Step 2 — Install Python via pyenv

```bash
pyenv install <version> --skip-existing
pyenv local <version>
```

Validate with:
```bash
python --version
```

The output must match the target version (e.g. *Python 3.13.x*). If not, stop and diagnose.

---

### Step 3 — Create the virtualenv manually with pyenv's Python

**Do NOT use `poetry env use`.** In Poetry `1.8.3`, that command validates the system Python
against the project constraint — if the system has a Python outside the constraint range
(e.g. Homebrew Python 3.13), it rejects the command even when you pass a valid Python path.

Instead, create `.venv` directly using the pyenv Python binary:

```bash
$(pyenv which python) -m venv .venv
```

Validate that the venv contains the right Python:
```bash
.venv/bin/python --version
```

The output must match the target version (e.g. `Python 3.13.13`). Stop and diagnose if not.

---

### Step 4 — Clear Poetry caches

Before installing dependencies, remove stale Poetry caches to avoid conflicts with previously cached packages:

```bash
rm -rf ~/Library/Caches/pypoetry/artifacts/
rm -rf ~/Library/Caches/pypoetry/cache/
rm -rf ~/Library/Caches/pypoetry/virtualenvs/
```

Note: these paths are macOS-specific. On Linux the cache lives under `~/.cache/pypoetry/` — adjust accordingly if the contributor is on Linux.

---

### Step 5 — Install project dependencies

Activate the virtualenv first, then run `poetry install`. When `VIRTUAL_ENV` is set in the
environment, Poetry uses it directly instead of resolving Python from the system PATH:

```bash
source .venv/bin/activate && poetry install
```

This installs the full dependency set. It may take several minutes.

---

### Step 6 — Set up pre-commit hooks

This project uses [pre-commit](https://pre-commit.com/) to keep code consistent
and properly structured. The hooks defined in `.pre-commit-config.yaml` run
linters, formatters, type checkers, security scanners, and tests before each
commit, plus a commit-message regex check on the `commit-msg` stage.

Run the four commands below in order. They must run inside the activated
virtualenv from Step 5 — `pre-commit` is a dev dependency, so `poetry run`
finds it in the project's venv.

```bash
# 1. If a previous pre-commit configuration is installed on this clone,
#    remove it first so the new hooks install cleanly.
poetry run pre-commit uninstall

# 2. Install this project's hooks. The '--config' flag is explicit (the file
#    is at the repo root, but stating it documents intent), and '--overwrite'
#    replaces any existing git hooks rather than aborting on conflict.
poetry run pre-commit install --config .pre-commit-config.yaml --overwrite

# 3. Clean cached hook environments to avoid stale tool versions left over
#    from previous installs.
poetry run pre-commit clean

# 4. Bump every hook repo (pre-commit-hooks, etc.) to its latest released
#    tag so checks like check-merge-conflict, check-json, detect-private-key
#    don't drift behind upstream.
poetry run pre-commit autoupdate
```

Validate by inspecting `.git/hooks/pre-commit` and `.git/hooks/commit-msg` —
both files should now exist and contain pre-commit's generated shim. If either
command above fails with "command not found", Step 5 did not complete
successfully; fix that before retrying.

---

### Step 7 — Run setup_local.sh

```bash
bash commands/setup_local.sh
```

This script installs the `local` optional dependency group and the Claude CLI. Failures here are non-blocking (the script already handles them with fallback messages). Show the output to the contributor and highlight any [ERROR] lines if present.

---

## Completion

When all steps succeed, confirm to the contributor:

- Python version active
- Poetry version (`1.8.3`)
- Poetry virtualenv path
- Whether `local` dependencies installed cleanly
- Whether Claude CLI installed cleanly

Then suggest next steps:
```bash
poetry shell        # Activate the virtualenv
pytest --no-cov     # Quick smoke test to verify the environment
```

Note: `poetry shell` works here because `virtualenvs.in-project = true` — Poetry finds the
`.venv` directory automatically. Use `poetry shell` for all day-to-day activation.
The `source .venv/bin/activate` used during Step 5 is only needed once at install time
to bypass the system Python constraint check bug in Poetry `1.8.3`.

---

## Error Handling Principles

- **Never skip a failed step silently** — always surface errors to the contributor;
- **Diagnose before retrying** — read the error message and explain what it means;
- **Non-blocking failures** (`setup_local.sh`) should be noted but must not abort the overall setup;
- **Blocking failures** (`pyenv`, `poetry version`, `poetry install`) require resolution before moving on.
