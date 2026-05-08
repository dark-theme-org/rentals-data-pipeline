---
name: commit
description: Stage, commit, and push the current branch end-to-end with project safety rails. Refuses commits to develop/master/main, never bypasses pre-commit hooks, never force-pushes.
user-invocable: true
allowed-tools: Bash, Read
---

# Commit Skill

Your task is to walk the contributor through staging, committing, and pushing
the current branch's work in a single guided flow. This skill is opinionated
about safety: it refuses commits to protected branches, never bypasses
pre-commit hooks, never force-pushes, and never stages with `git add -A` /
`git add .` (which can sweep up sensitive files like credentials).

## Language

Interact with the user in the same language they used to invoke the skill.

## Hard rules — never violate these

- ❌ **Protected branches**: refuse to commit if the current branch is
  `develop`, `master`, or `main`. The contributor must switch to a
  `feature/*`, `fix/*`, or `enhancement/*` branch first.
- ❌ **Never** run `git add -A`, `git add .`, or `git add --all`. Always
  list explicit paths.
- ❌ **Never** use `git commit --no-verify` or `--amend` unless the
  contributor explicitly requests it. If a pre-commit hook fails, fix the
  underlying issue and create a new commit.
- ❌ **Never** use `git push --force` or `--force-with-lease` unless the
  contributor explicitly requests it.
- ❌ **Never** auto-resolve a divergent push (don't auto-pull / auto-rebase).
  Surface the situation and let the contributor decide.
- ✅ Always show the contributor what's about to happen before each
  side-effecting action (stage, commit, push) and accept overrides.

## Security mindset — read this before staging anything

Leaking a credential into git history is hard to undo and may force the
contributor to rotate keys, revoke tokens, or notify ops. **Treat every
file as potentially containing secrets**, even if its name looks
innocuous. A file named `config.json`, `notes.md`, or `helpers.py` can
still hold an API key, a service-account JSON, or a database URL with
embedded credentials.

Defense in depth — apply every layer:

1. **Filename patterns** (Step 3) are a first-pass filter, not the
   source of truth.
2. **Scan diff content** for these markers before staging:
   - PEM private-key headers — match the regex
     `[-]{5}BEGIN ([A-Z]+ )?PRIVATE KEY[-]{5}`. This catches RSA, DSA,
     EC, OpenSSH, encrypted, and unlabeled private keys (algorithm name
     appears between `BEGIN` and `PRIVATE KEY`).
   - Certificate headers — match `[-]{5}BEGIN CERTIFICATE[-]{5}`.
   - Cloud credential fields in JSON: `"private_key"`, `"client_email"`,
     `"private_key_id"`
   - Provider-specific token prefixes: `AKIA[0-9A-Z]{16}` (AWS),
     `xox[abprs]-` (Slack), `ghp_` / `ghs_` / `gho_` / `ghu_` / `ghr_`
     (GitHub), `glpat-` (GitLab)
   - Generic secret markers: `password=`, `passwd=`, `secret=`,
     `api_key=`, `apikey=`, `token=`, `access_key=`, `bearer ` followed
     by a high-entropy string
   - Database URLs with embedded credentials:
     `://user:password@host` patterns
3. **When in doubt, ask.** It is always cheaper to pause and confirm
   than to leak a credential and rotate it later.

If the staged diff contains any of these markers, the skill **must**
flag the file and refuse to commit until the contributor either
(a) unstages it, (b) replaces the secret with an environment-variable
reference, or (c) explicitly confirms the value is a placeholder or
an already-revoked credential.

The pre-commit hook `detect-private-key` (configured in
`.pre-commit-config.yaml`) catches PEM-format keys at commit time as a
last-line defense. **Do not rely on it as the only defense** — the goal
is to catch issues during staging, before the commit fires.

## Overview of Steps

1. Preflight — repo state, current branch, no in-progress merge or rebase
2. Surface what's pending — staged / modified / untracked files
3. Stage the right files — by default everything pending, gated per-file by the security scan
4. Draft and validate a commit message — single-line or multi-line based on scope
5. Commit — handle pre-commit auto-fixes and hard failures
6. Confirm and push
7. Report — commit SHA, branch, next steps

---

## Step-by-Step Instructions

### Step 1 — Preflight

Run these checks. Stop and surface the error if any fails.

```bash
# Confirm we're inside a git working tree
git rev-parse --is-inside-work-tree

# Read the current branch
git rev-parse --abbrev-ref HEAD
```

**If the current branch is `develop`, `master`, or `main`:** abort
immediately. Tell the contributor:

> Refusing to commit to `<branch>`. This branch is protected.
> Switch to a `feature/*`, `fix/*`, or `enhancement/*` branch first
> (e.g. `git checkout -b feature/your-change`) and re-run `/commit`.

**Check for in-progress operations:** if `.git/MERGE_HEAD` or
`.git/REBASE_HEAD` exists, abort and tell the contributor to finish or
abort the merge / rebase before continuing.

**Verify pre-commit is installed and wired into git.** This skill
relies on the project's pre-commit hooks for linting, formatting,
security scanning, and the commit-msg prefix check. If any of these
checks fails, abort:

```bash
# 1. pre-commit is available in the project's venv
poetry run pre-commit --version

# 2. .git/hooks/pre-commit and .git/hooks/commit-msg are wired to
#    pre-commit's shim
grep -q "pre-commit" .git/hooks/pre-commit
grep -q "pre-commit" .git/hooks/commit-msg
```

If pre-commit is missing or the git hooks aren't wired, tell the
contributor:

> Pre-commit is not installed correctly on this clone. The hooks
> defined in `.pre-commit-config.yaml` are this project's safety net —
> without them the commit will skip linting, formatting, security
> scanning, and the commit-msg prefix check.
>
> Run `/setup` (specifically Step 6 — Set up pre-commit hooks) to
> install everything, then re-run `/commit`.

---

### Step 2 — Surface what's pending

```bash
git status --short
git diff --stat
```

Summarize for the contributor:

- Number of files staged, modified, untracked
- Whether the branch is ahead / behind its remote upstream

**Edge cases:**

- **Working tree clean and branch is ahead of remote** → skip Steps 3–5
  (nothing new to commit) and go straight to Step 6 to push existing
  commits.
- **Working tree clean and branch is up to date with remote** → exit
  cleanly with "Nothing to do".

---

### Step 3 — Stage the right files

By default, this skill stages **every** pending change shown by
`git status` — modified files, untracked files, deletions, and any
needed untracking (e.g. `.python-version` if it's in `.gitignore` but
still tracked) — and packs them all into a single commit. This avoids
fragmenting related work across many tiny commits. The contributor may
override the default by listing specific paths to include or exclude.

**Apply the Security mindset section before staging anything.** Every
file that would be added must pass two layers of checks first:

**Layer 1 — flag risky filenames** and require explicit opt-in for
each match:

- `.env` / `.env.*`
- `*credentials*` / `*service-account*` / `*.gcp.json`
- `*.key` / `*.pem`
- Any file larger than 500 KB

**Layer 2 — scan the diff content** of every file about to be staged.
For each path, run `git diff <path>` (or `git diff --cached <path>` if
already staged, or `cat <path>` for new untracked files) and grep for
the secret markers listed in the Security mindset section above
(PEM headers, cloud credential JSON keys, token prefixes, generic
`password=` / `secret=` / `token=` patterns, embedded-credential
database URLs).

If any file's diff or content contains a secret marker, **refuse to
stage** that file until the contributor either:

- removes the secret and replaces it with an environment-variable
  reference (e.g. `os.environ["API_KEY"]`); or
- excludes the file from this commit; or
- explicitly confirms the matched value is a documented placeholder or
  an already-revoked credential.

After every file passes the scan, stage them with one `git add`
listing each path explicitly:

```bash
git add path/one path/two path/three
```

Do **not** use `git add -A`, `git add .`, or `git add --all`. The
harness forbids these because they can sweep up sensitive files. The
explicit-path list above is how we get "everything pending" while
preserving the per-file security review.

For files that need to be **untracked** (matched by `.gitignore` but
still in the index — e.g. `.python-version`), use
`git rm --cached <path>` instead of `git add`. This stages the
untracking without removing the file from disk.

The contributor may override the default at any point by:

- Listing specific paths to stage (narrows the scope)
- Listing specific paths to exclude (keeps everything else)

---

### Step 4 — Draft and validate the commit message

Read recent log entries to match repo style:

```bash
git log -10 --oneline
```

Analyze what's being committed:

```bash
git diff --staged --stat
git diff --staged
```

**Decide message length based on the staged changes:**

- **Single-line message** — for small, single-theme commits (about
  five or fewer files, or a single coherent change). Matches the
  repo's existing short-message style.
- **Multi-line message** (subject line + blank line + bulleted body)
  — for larger or multi-themed commits where one line cannot capture
  the breadth. Group the body bullets thematically (skills, configs,
  docs, tooling bumps, etc.).

The decision is the skill's, based on `git diff --staged --stat`:
high file count or mixed themes ⇒ multi-line; otherwise one-line.
Show the proposal to the contributor and accept overrides.

Either way, the **subject line** has this form:

```
<prefix>: <short description in the imperative>
```

`<prefix>` must be one of: `analysis`, `change`, `feature`, `fix`,
`refactor`, `test`. Defined in `.pre-commit-config.yaml`'s
`commit-msg` hook.

For multi-line messages, leave a blank line after the subject and
group the body as bullets. The commit-msg hook uses
`pygrep --multiline --negate`, so the regex below must match
**somewhere** in the message — the subject line is what matches, not
the body bullets.

**Validate** the message against this regex before proceeding:

```
^((analysis|change|feature|fix|refactor|test): .*|Merge .*)$
```

If the contributor provides a custom message that fails the regex,
ask them to revise. Never commit with an invalid message and never
bypass the hook.

---

### Step 5 — Commit

Use a heredoc to preserve message formatting:

```bash
git commit -m "$(cat <<'EOF'
<approved message>
EOF
)"
```

Pre-commit hooks fire automatically. `fail_fast: true` is set, so the
first failing hook stops the run.

**If the commit fails because hooks auto-modified files** (`black`,
`autoflake`, `isort`):

1. Show the contributor a `git diff` of what was auto-fixed.
2. Re-stage the same explicit paths from Step 3.
3. Retry the commit with the same approved message.
4. Loop at most twice. If a third attempt is needed, bail and ask the
   contributor to investigate manually.

**If the commit fails on a hard failure** (`flake8`, `pylint`, `mypy`,
`bandit`, `pytest`):

1. Surface the full hook output to the contributor.
2. Leave staging intact so they can investigate.
3. Tell them to fix the issue and re-run `/commit`.
4. **Do not retry with `--no-verify`.**

---

### Step 6 — Confirm and push

Pushing is a shared-state action. Always ask before pushing, even though
the contributor invoked `/commit`:

> Push commit `<sha>` to remote? (y/n)

If they decline, exit cleanly. The commit stays local; they can push
manually later.

If they confirm, detect upstream tracking:

```bash
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null
```

- **Branch tracks a remote** → `git push`
- **No upstream set** (first push for this branch) →
  `git push -u origin <current-branch>`

**Before pushing, fetch and check for divergence:**

```bash
git fetch
git status -uno
```

If the local branch is behind the remote (someone else pushed), abort
the push and tell the contributor to run `git pull --rebase` first.
**Do not auto-pull.**

**Never** pass `--force` or `--force-with-lease` unless the contributor
explicitly says "force push" — even then, double-check that the target
branch is not `develop` / `master` / `main`.

---

### Step 7 — Report

Print:

- New commit SHA (`git rev-parse HEAD` after the push)
- Branch name
- Remote URL (`git remote get-url origin`)
- Summary of what was pushed (file count, +/- lines from
  `git show --stat HEAD`)

If this was the first push of the branch, also surface the GitHub URL
the contributor can click to open a PR — usually
`https://github.com/<owner>/<repo>/pull/new/<branch>`.

---

## Error Handling Principles

- **Never skip a failed step silently** — always surface errors.
- **Diagnose before retrying** — read the error message, explain what it
  means, then decide on the next action.
- **Hard failures stop the flow** — don't muscle through a failed hook
  by bypassing it.
- **The contributor is the source of truth** — when in doubt about
  staging, message wording, or whether to push, ask.

## Refusal triggers

The skill must refuse and explain when:

- The current branch is `develop`, `master`, or `main`.
- A merge or rebase is in progress.
- **Pre-commit is not installed or the git hooks are not wired** —
  redirect the contributor to `/setup` Step 6.
- **A staged diff contains a secret marker** (PEM header, cloud
  credential JSON key, token prefix, plaintext password, etc.) and
  the contributor has not removed it, unstaged the file, or
  explicitly confirmed the value is a placeholder / already-revoked.
- A pre-commit hook fails with a hard error and the contributor has
  not yet fixed the underlying issue.
- The contributor asks the skill to push to a protected branch,
  force push without explicit intent, bypass hooks, or stage
  credentials.
