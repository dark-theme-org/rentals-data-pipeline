---
name: pr
description: Open a pull request from the current feature branch into a target branch — defaults to `develop` or `main`, but the contributor may override to any branch via the target-branch gate. Auto-fills the project's PR template, resolves assignee/labels/title/body; asks only the target branch and whether to open as draft or ready for review. Uses the `gh` CLI for all GitHub API calls.
user-invocable: true
allowed-tools: Bash, Read
---

# PR Skill

Your task is to open a GitHub pull request from the current non-protected
branch into a target branch — typically a protected branch (`develop`
or `main`), but the contributor may override to any branch via the
target-branch gate. The skill auto-fills the project's PR template by
analyzing the branch diff, picks labels from the repo's existing label
set, assigns the contributor, drafts the title, and asks exactly two
questions: **which target branch?** and **draft or ready for review?**

Anything not represented in the four template sections (`Goal`, reviewer
entry points, QA, Other) can be edited later in the GitHub web UI.

## Language

Interact with the user in the same language they used to invoke the skill.

## Tooling — `gh` CLI for all GitHub API calls

Every GitHub-side action goes through the `gh` CLI. The skill does
**not** use the GitHub MCP, because per-account auth is simpler to
manage with `gh` (one keychain entry per host, switchable with
`gh auth switch`) than with MCP (which requires re-configuring the
server with a different PAT for each account).

| Operation                                 | Command                                                |
|-------------------------------------------|--------------------------------------------------------|
| Authenticated user lookup                 | `gh api user --jq .login`                              |
| Auth status / which account is active     | `gh auth status`                                       |
| Existing-PR check by head branch          | `gh pr list --head <branch> --state open --json url,number` |
| Discover existing labels                  | `gh label list --limit 100 --json name,description`    |
| Create the PR                             | `gh pr create`                                         |
| Apply labels / assignees post-create      | `gh pr edit <PR number> --add-label … --add-assignee …`|
| Local git inspection                      | `git` CLI (always local; no API call)                  |

Local git operations — `git fetch`, `git log`, `git diff`,
`git show-ref`, `git rev-parse`, `git status`, `git remote get-url` —
always run locally; they aren't GitHub-API operations and don't need
`gh`.

## Hard rules — never violate these

- ❌ **Source branch must be non-protected.** Refuse if the current branch
  is `develop` or `main`. The contributor must be on a
  `feature/*`, `fix/*`, or `enhancement/*` branch first.
- ✅ **Target branch defaults to a protected branch but is overridable.**
  The Step-2 gate offers detected protected branches (`develop` / `main`)
  as named options; the contributor may override to any branch
  (including a non-protected one) by typing it in the auto-provided
  `Other` input. The skill never silently picks a target — it always
  asks.
- ❌ **Branch must be pushed** to `origin` and not divergent from the
  remote. If not, abort and direct the contributor to `/commit` (which
  pushes) or to `git push` manually.
- ❌ **Never create a duplicate PR.** If an open PR already exists for
  this branch, surface its URL and exit cleanly.
- ❌ **Never create labels** that don't already exist in the repo. If no
  existing label matches the PR scope, skip the label step entirely.
- ❌ **Never assign anyone other than the authenticated `gh` user.**
  The assignee is always the login returned by `gh api user --jq .login`.

## Confirmation gates — two explicit asks, everything else auto

The skill exposes exactly **two confirmation gates**. Use the
`AskUserQuestion` tool at each one:

1. **Target branch** (Step 2) — list the detected protected branches
   (`develop` / `main`) as named options and ask which one to target;
   the contributor may also type any other branch via the
   auto-provided `Other` input.
2. **Draft vs ready** (Step 8) — ask whether to open the PR as a
   **draft** or **ready for review**.

Every other step (preflight, existing-PR check, diff analysis, label
detection, assignee resolution, title drafting, template fill, the
post-create label/assignee application, the final report) runs
**automatically without asking**. The skill only pauses outside these
gates when it must surface a blocking issue:

- protected source branch
- branch has no upstream / is ahead of remote / is divergent from remote
- a PR already exists for this branch
- `gh` not installed or not authenticated
- `gh pr create` itself fails (e.g. typed target doesn't exist on the
  remote)

## Overview of Steps

1. Preflight — local git tree, branch is non-protected, upstream set,
   branch pushed and not divergent; resolve `owner`/`repo` from the
   origin URL; confirm `gh` is installed and authenticated; check for
   an existing open PR
2. **Gate 1 — ask which target branch** to PR into
3. Gather diff data — commits, file stats, categorize files into buckets
4. Resolve the assignee — the login captured in Step 1
5. Detect labels — discover existing labels via `gh label list`, match
   against commit prefixes and file buckets
6. Draft the PR title — **sentence case, no commit prefix**
7. Fill the PR template — Goal, reviewer entry points, QA, Other
8. **Gate 2 — ask draft vs ready**
9. Create the PR via `gh pr create`
10. Apply labels and assignees via `gh pr edit`
11. Report — PR URL and number

---

## Step-by-Step Instructions

### Step 1 — Preflight

Run the local git checks in parallel:

```bash
git rev-parse --is-inside-work-tree
git rev-parse --abbrev-ref HEAD
git remote get-url origin
```

Parse `owner` and `repo` from the origin URL. Both forms must be
handled:

- HTTPS: `https://github.com/<owner>/<repo>.git`
- SSH:   `git@github.com:<owner>/<repo>.git`

Strip the trailing `.git` if present. If the remote isn't a GitHub
URL, abort: `/pr` only supports GitHub remotes.

**If the current branch is `develop` / `main`:** abort
immediately:

> Refusing to open a PR from `<branch>`. PRs must originate on a
> non-protected branch (`feature/*`, `fix/*`, or `enhancement/*`).
> Switch to a feature branch and try again.

**Confirm `gh` is installed and authenticated:**

```bash
gh auth status
gh api user --jq .login
```

If `gh` is not installed (`command not found`), abort with:

> The `gh` CLI is not installed. Install it with `brew install gh` on
> macOS, then run `gh auth login` and re-run `/pr`.

If `gh auth status` reports no active account, abort with:

> `gh` is installed but not authenticated. Run `gh auth login`, sign
> in to the account you want this PR opened under, then re-run `/pr`.

Capture the login returned by `gh api user --jq .login` for the
assignee step (Step 4 / Step 10).

**Verify the branch is pushed and synced with the remote:**

```bash
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null
git fetch origin
git status -uno -sb | head -1
```

Abort and redirect the contributor when:

- **No upstream set** (branch never pushed) → run `/commit` or
  `git push -u origin <branch>` first.
- **Branch ahead** of remote → run `/commit` to push, or push manually.
- **Branch behind or diverged** → run `git pull --rebase`, resolve,
  then re-run `/pr`.

**Soft warning, not a refusal:** if `git status --porcelain` shows
unstaged or untracked changes, surface a one-line warning that those
changes won't be in the PR. Continue the flow.

**Check for an existing PR on this branch:**

```bash
gh pr list --head <current-branch> --state open --json url,number,title --limit 5
```

If the result is non-empty, surface the existing PR URL and exit
cleanly. Do not attempt to create a duplicate.

### Step 2 — Gate 1: ask which target branch

Use `git show-ref` locally to discover which conventional protected
branches exist on the remote (the refs are already cached locally
after `git fetch origin` in Step 1):

```bash
for candidate in develop main; do
  if git show-ref --verify --quiet "refs/remotes/origin/$candidate"; then
    echo "$candidate"
  fi
done
```

Build the `AskUserQuestion` options:

- One option per **detected** protected branch — `develop` first when
  present, then `main`.
- A `Cancel` option (always included).
- **Edge case** — if neither `develop` nor `main` exists on the remote
  (rare), include both as named options anyway so the question still
  has the minimum 2 explicit options. The auto-`Other` input handles
  every non-default target regardless.

The contributor **may override the recommended defaults** by picking
the auto-provided `Other` input on the question and typing any branch
name — this is how a PR against a non-protected branch (for example,
when stacking onto another feature branch) is opened. The skill
honors the contributor's explicit choice without checking that the
target is protected.

Use `AskUserQuestion`:

> Which branch should this PR target?
>
> Options (built from detected protected branches + Cancel):
> - `develop` — long-running integration branch (recommended default
>   when present)
> - `main` — production / release branch (when present)
> - Cancel — abort without creating a PR
>
> _Tip: pick `Other` to type any branch name — including a
> non-protected branch you're stacking on top of._

Capture the chosen target as `$TARGET`. The skill **does not
pre-validate** that `$TARGET` exists on the remote; if the contributor
typed a typo or a branch that hasn't been pushed, `gh pr create` in
Step 9 will fail with a clear error and the skill surfaces it.

### Step 3 — Gather diff data

```bash
TARGET=<from Step 2>

# Commits in this branch but not in target, oldest first; skip merges
git log "$TARGET..HEAD" --reverse --no-merges --pretty=format:"%h %s"

# Stat-level summary
git diff --stat "$TARGET...HEAD"

# Full file list with status (A/M/D/R)
git diff --name-status "$TARGET...HEAD"
```

If `git log "$TARGET..HEAD"` is empty, abort: nothing to PR.

Categorize the changed files into buckets to drive both the
**reviewer entry points** (Step 7) and **label detection** (Step 5):

- **Source code** — `src/**/*.py`
- **Tests** — `tests/**/*.py`
- **Project config** — `pyproject.toml`, `poetry.lock`,
  `.pre-commit-config.yaml`, `.code_quality/**`
- **Docs / repo meta** — `*.md`, `docs/**`, `.github/**`
- **Claude harness** — `.claude/**` (skills, settings, memory)
- **Operational scripts** — `commands/**`
- **Notebooks** — `notebooks/**`

### Step 4 — Resolve the assignee

The login was captured in Step 1 from `gh api user --jq .login`. Use
that login as the single entry passed to `gh pr edit --add-assignee`
in Step 10. Never assign anyone else.

### Step 5 — Detect labels

Discover the repo's existing labels:

```bash
gh label list --limit 100 --json name,description
```

Build a candidate set by intersecting these signals with the
available label names (case-insensitive substring match):

| Signal                                                | Candidate labels         |
|-------------------------------------------------------|--------------------------|
| Commits with prefix `feature`                         | `feature`, `enhancement` |
| Commits with prefix `fix`                             | `bug`, `fix`             |
| Commits with prefix `change`                          | `change`                 |
| Commits with prefix `refactor`                        | `refactor`               |
| Commits with prefix `test`                            | `tests`, `testing`       |
| Commits with prefix `analysis`                        | `analysis`               |
| Tests bucket non-empty                                | `tests`                  |
| Docs bucket dominant (>50% of changed files)          | `documentation`, `docs`  |
| Claude harness bucket non-empty                       | `tooling`, `claude`      |
| Project config bucket non-empty                       | `config`, `dependencies` |

Pass only labels that **actually exist** in the repo. Cap the final
set at 3–4 — pick the most representative.

If `gh label list` fails (e.g. transient API error), skip the label
step entirely; the PR will be created without labels and the
contributor can add them in the GitHub UI.

### Step 6 — Draft the PR title

**Style: sentence case, no commit prefix.** The PR title is **not**
required to follow the project's commit-prefix convention (no
`feature:` / `change:` / `fix:` etc.). It is a clean, human-readable
summary of the branch's main change.

Rules:

- **Lead with a capital letter.**
- **No prefix** — strip any `<prefix>:` borrowed from a commit subject.
- **Lowercase the natural-language words** that follow the leading
  capital.
- **Preserve the original casing of identifiers** — file paths
  (`CLAUDE.md`, `pyproject.toml`), slash-commands (`/commit`, `/pr`),
  code symbols, proper nouns (GitHub, Python), and acronyms (CI, PR).
  The "lowercase rest" rule applies only to ordinary words.
- **Keep under ~70 characters.**
- **No trailing period.**
- **Imperative or noun-phrase form** — both fit; pick whichever reads
  more naturally.

Examples:

- ✅ `Initial project scaffolding with /commit and /setup skills`
- ✅ `Add three confirmation gates to /commit skill`
- ✅ `Migrate dbt-bigquery to 1.11.x and pin Python 3.13`
- ❌ `feature: initial project scaffolding…` (has prefix)
- ❌ `Initial Project Scaffolding…` (Title Case, not sentence case)
- ❌ `initial project scaffolding…` (no leading capital)

How to draft:

- **Single non-merge commit on the branch** → take the commit subject,
  drop the `<prefix>:` and the leading space, capitalize the first
  letter of the result, leave the rest as-is.
- **Multiple commits** → write a one-line summary capturing the
  branch's overall outcome, applying the rules above. Lead with the
  value of the change ("Add X", "Refactor Y", "Fix Z"), not the
  mechanism.

### Step 7 — Fill the PR template

Read the template:

```bash
cat .github/pull_request_template.md
```

If the file does not exist, fall back to a minimal body containing
the same four sections (Goal, reviewer entry points, QA, Other) —
keep the emoji headings and `* [ ]` checkbox style.

Fill each section based on the diff data from Step 3. **Strip the
template's instructional placeholder text** ("Explain the main
goal…", "Highlight files…", "Tell us what kind of tests…", "Add
informational resources…") once the section is filled — those
prompts are for the author, not for the final body.

**`## :dart: Goal`** — 2–4 sentences describing what the PR does and
why. Synthesize from commit subjects and the dominant file buckets.
Lead with the outcome ("Adds X", "Refactors Y", "Fixes Z"), not the
mechanism. Avoid restating the diff line by line.

**`## :bulb: Where should the reviewer start?`** — list 3–7 of the
most impactful changed files as `* [ ]` checkboxes (preserve the
unchecked boxes; reviewers tick them as they read). Prefer:

- Newly added files over modified ones (when both are present)
- Files with the largest line-delta from `git diff --stat`
- Module entry points (`__init__.py`, top-level scripts, `SKILL.md`s)
  over leaf helpers

When a single function inside a file carries the change, use
`path::function` form (matching the template's example). Otherwise
use the bare path. Wrap each path in backticks.

**`## :ballot_box_with_check: Quality Assurance (QA)`** — list the
test files added or modified in the **Tests** bucket as `* [ ]`
checkboxes (prefer `tests/path/to/test_file.py::test_function` form
when the change is at function level). If the Tests bucket is empty,
replace the bullet list with a short italicized note explaining how
the change was verified, e.g.:

> _No new tests in this PR — changes are limited to skill instructions
> and project documentation; pre-commit hooks (lint, format, security,
> commit-msg) ran clean on every commit in the range._

**`## :link:/:camera: Other relative informations`** — include only
context the diff cannot reveal: linked issues from commit trailers
(`Refs #123`, `Closes #456`), screenshots / CURLs the contributor
mentioned in commit bodies, links to design docs. If nothing applies,
replace the bullet with `_None_`.

### Step 8 — Gate 2: draft vs ready

Use `AskUserQuestion`. Show everything that's about to be sent so the
contributor can sanity-check before creation:

> Open this PR as a draft or ready for review?
>
> - **Title:** `<drafted title>`
> - **Base:** `<target>` ← **Head:** `<current-branch>`
> - **Assignee:** `<gh login>`
> - **Labels:** `<comma-separated detected labels>` (or `none`)
>
> Options:
> - Ready for review — opens the PR with reviewers able to engage
> - Draft — opens as a draft (won't request review until marked ready)
> - Cancel — abort without creating a PR

### Step 9 — Create the PR

Write the filled template body to a temp file (avoids quoting issues
with multi-line markdown), then call `gh pr create`:

```bash
BODY_FILE=$(mktemp)
cat > "$BODY_FILE" <<'EOF'
<filled template body>
EOF

gh pr create \
  --base "$TARGET" \
  --head "<current-branch>" \
  --title "<drafted title>" \
  --body-file "$BODY_FILE" \
  $( [ "$DRAFT" = "true" ] && echo "--draft" )
```

`gh pr create` prints the PR URL on stdout on success. Capture it
and parse the PR number from the trailing path segment (e.g. `/pull/42`
→ `42`) — both are needed for Step 10 and Step 11.

If the call fails (network, permissions, branch protection rules,
typed target doesn't exist, etc.), surface the full `gh` error to the
contributor — do not retry blindly.

### Step 10 — Apply labels and assignees

`gh pr create` does not accept `--label` / `--assignee` reliably for
non-collaborator users in some configurations, and the cleanest path
is a follow-up `gh pr edit`:

```bash
gh pr edit <PR number> \
  --add-assignee "<gh login>" \
  $( [ -n "$LABELS" ] && echo "--add-label" "$LABELS" )
```

Where `$LABELS` is the comma-separated list of labels detected in
Step 5 (e.g. `feature,tooling,claude`).

Notes:

- Always include `--add-assignee <login>`.
- Include `--add-label` only if Step 5 detected at least one existing
  label; otherwise omit the flag. Never invent labels.
- If this edit call fails (label name no longer exists, permissions,
  etc.), surface the error but **do not delete the PR** — the PR was
  created successfully and the contributor can adjust labels /
  assignees in the GitHub UI.

### Step 11 — Report

Print:

- PR URL (from `gh pr create` stdout)
- PR number, title, base ← head
- Whether it was opened as draft
- Detected labels and resolved assignee
- One-line reminder: *"The Goal / reviewer entry points / QA / Other
  sections were auto-drafted from the branch diff — refine them in
  the GitHub web UI if anything needs sharpening."*

---

## Error Handling Principles

- **Never skip a failed step silently** — surface every error.
- **Hard failures stop the flow** — don't muscle through a missing
  upstream, missing authentication, or duplicate PR.
- **Stay inside the auto-fill contract** — only assignee and labels
  are auto-resolved; reviewers, projects, milestones, and any other
  PR fields are left for the GitHub web UI.

## Refusal triggers

The skill must refuse and explain when:

- The current branch is `develop` / `main`.
- `gh` is not installed, or `gh auth status` reports no active account.
- The branch has no upstream, is ahead of the remote, or is divergent
  from it.
- A PR already exists for this branch (surface the URL).
- The contributor asks the skill to create labels that don't exist
  in the repo, or assign someone other than the authenticated `gh`
  user.
