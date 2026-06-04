---
name: terraform
description: Manage GCP infrastructure for the rentals data pipeline through the standard Terraform flow — preflight, init, fmt + validate, plan, gated apply (or destroy). Halts on any failure.
user-invocable: true
allowed-tools: Bash, Read, AskUserQuestion
---

# Terraform Skill

Your task is to walk the contributor through changing the project's GCP infrastructure end-to-end using the standard Terraform workflow defined in [terraform/README.md](../../../terraform/README.md). The skill assumes the `.tf` files in `terraform/` already reflect the desired state — the contributor edits them manually beforehand. The skill is the executor: it preflights the environment, validates the config, plans, asks for confirmation, then applies.

The skill **never modifies `.tf` files**. If formatting drift is detected, it offers to run `terraform fmt` (which only rewrites whitespace), but it does not author or change resource declarations.

## Language

Interact with the contributor in the same language they used to invoke the skill.

## Hard rules — never violate these

- ❌ **Never** run `terraform apply` directly. Always go through `terraform plan -out=tfplan.out` followed by `terraform apply tfplan.out`. The saved plan is the artifact the contributor approves; applying without a plan file would be applying something they didn't see.
- ❌ **Never** pass `-auto-approve` to `terraform apply` unless using a saved plan file (which already encodes the contributor's approval at gate 2).
- ❌ **Never** call `terraform destroy` directly. Use `terraform plan -destroy -out=tfplan.out` first, surface the plan, then `terraform apply tfplan.out`.
- ❌ **Never** run `terraform init -reconfigure` or `-migrate-state` autonomously. Both can move state between backends; surface the situation and let the contributor decide.
- ❌ **Never** edit `.tf` files. The contributor authors infra; this skill executes it.
- ❌ **Never** run `gcloud projects create`, `gcloud billing projects link`, `gcloud services enable`, or `gcloud storage buckets create` autonomously. Bootstrap is out of scope — see [terraform/README.md](../../../terraform/README.md) Prerequisites and follow them manually if needed.
- ❌ **Never** advance past a failed step. If init, validate, plan, or apply fails, surface the full error and stop.
- ✅ Always show what's about to happen at each gate before any side-effecting action.

## Confirmation gates — two explicit asks, everything else auto

The skill exposes exactly **two confirmation gates**. Use the `AskUserQuestion` tool at each.

1. **Action** (Step 5) — apply pending changes / destroy infrastructure / plan-only (read-only).
2. **Execute** (Step 7) — after `terraform plan` runs and the summary is shown, confirm whether to apply the saved plan.

Every other step (preflight, init detection, fmt check, validate, plan generation, post-apply report) runs **automatically without asking**. The skill only pauses outside these gates when it must surface a blocking issue:

- `terraform` CLI not installed
- `terraform/` directory missing
- Application Default Credentials not set
- Backend mismatch detected by `terraform init`
- `terraform fmt -check` shows drift (skill asks once whether to auto-fix)
- `terraform validate` fails
- `terraform plan` fails (auth, name conflict, missing GCP project, etc.)
- `terraform apply` fails

## Overview of Steps

1. Preflight — `terraform` CLI present, `terraform/` directory exists, ADC available
2. Init check — run `terraform init` if `.terraform/` is missing or stale
3. Format check — `terraform fmt -check -diff`, offer to auto-fix if drift
4. Validate — `terraform validate` must pass before going further
5. **Gate 1 — Action**: apply / destroy / plan-only
6. Plan — `terraform plan` (or `-destroy`), save to `tfplan.out`, surface summary
7. **Gate 2 — Execute**: confirm the plan, then apply (or stop if plan-only)
8. Report — outputs, state location, what changed

---

## Step-by-Step Instructions

### Step 1 — Preflight

Run these checks. Stop and surface the error if any fails.

```bash
# 1. terraform CLI is installed
command -v terraform
terraform version

# 2. terraform/ directory exists at repo root
test -d terraform && echo "terraform/ exists"

# 3. Application Default Credentials are set (the GCS backend and the google
#    provider both authenticate via ADC)
gcloud auth application-default print-access-token >/dev/null 2>&1 \
  && echo "ADC OK" || echo "ADC NOT SET"
```

**If `terraform` is missing:** tell the contributor to install it (`brew install terraform` on macOS) and stop.

**If `terraform/` is missing:** stop and tell the contributor that this skill operates on the project's `terraform/` directory, which doesn't exist.

**If ADC is not set:** stop and tell the contributor:

> Application Default Credentials are not configured. The Terraform GCS backend and the google provider both need them. Run:
>
> ```bash
> gcloud auth application-default login
> ```
>
> Pick the Google account with access to both `darktheme-ops` (state) and `rentals-data-pipeline` (resources) in the browser, then re-run `/terraform`.

After this point, every subsequent command runs from inside the `terraform/` directory:

```bash
cd terraform/
```

---

### Step 2 — Init check

Check whether `.terraform/` exists. If it does, also detect whether the backend or providers might have changed since the last init.

```bash
test -d .terraform && echo "initialized" || echo "needs init"

# Cheap drift check — terraform init exits 0 quickly when nothing has changed
terraform init -input=false -backend=true 2>&1
```

**If `.terraform/` is absent**, run `terraform init -input=false` and surface the output. If init prints a backend-migration prompt or asks to reconfigure, **stop** — do not auto-answer. Tell the contributor:

> `terraform init` is asking about backend migration or reconfiguration. This skill never moves state between backends autonomously. Either accept the change manually with `terraform init -migrate-state` (or `-reconfigure`) outside the skill, or revert your `terraform.tf` change so the backend matches the existing state.

**If init succeeds cleanly**, continue.

---

### Step 3 — Format check

```bash
terraform fmt -check -diff
```

- **Exit code 0**: no drift, continue.
- **Non-zero exit code**: at least one file is not canonically formatted. Surface the diff to the contributor and ask once via `AskUserQuestion`:

> `terraform fmt` would rewrite the formatting of N file(s). Auto-fix now?
>
> Options:
> - Auto-fix (run `terraform fmt`)
> - Skip (continue without fixing)
> - Cancel

If they pick **Auto-fix**, run `terraform fmt` (no flags) and continue. If **Skip**, continue. If **Cancel**, exit cleanly.

`terraform fmt` only touches whitespace — it never alters resource declarations or values, so auto-fixing is safe and reversible.

---

### Step 4 — Validate

```bash
terraform validate
```

Validate is fast and offline. If it fails, surface the full error and **stop**. Do not attempt to repair `.tf` files automatically — surface the message and let the contributor edit.

---

### Step 5 — Gate 1: Action

Use `AskUserQuestion`:

> What should I do?
>
> Options:
> - **Apply pending changes** — generate a plan and apply it (default)
> - **Destroy infrastructure** — generate a destroy plan and tear down all managed resources
> - **Plan only** — generate the plan and stop (read-only; no apply)
> - Cancel

Record the choice as `<action>`. If **Cancel**, exit cleanly.

---

### Step 5b — Collect variable values

Before planning, parse `terraform/variables.tf` to discover **every** declared variable and its default (if any). Ask the contributor for the value of each variable, regardless of whether it has a default.

Use `AskUserQuestion` (one question per variable, up to 4 per call; make multiple calls if needed):

- **question**: `"Value for <variable_name>?"`
- **header**: `<variable_name>`
- **options**:
  - If the variable **has a default**: first option is `label: "<default>"`, `description: "Default value"`. Include a second meaningful option where applicable (e.g. `"prod"` for an environment variable).
  - If the variable **has no default**: offer a contextual suggestion as the first option (e.g. `"dev"` for a version tag), clearly labelled as a suggestion. Include a second option where applicable.
  - The automatic **Other** option always appears, letting the contributor type any custom value.
- **multiSelect**: `false`

Collect all answers. Pass every variable to the plan command as `-var="<name>=<value>"` flags. Never silently use a default or fill in a value without asking.

---

### Step 6 — Plan

Generate a plan and save it to `tfplan.out`. The plan file is the exact artifact that will be applied at gate 2 — no re-planning happens between approval and apply.

```bash
# For "Apply pending changes" or "Plan only"
terraform plan -input=false -out=tfplan.out -var="<name>=<value>" ...

# For "Destroy infrastructure"
terraform plan -destroy -input=false -out=tfplan.out -var="<name>=<value>" ...
```

If `plan` fails (auth error, GCP API error, name conflict, missing project, etc.), surface the full error and **stop**. Common causes — note these in the error report:

- `Error 403: ... does not have storage.buckets.create access` → ADC account lacks permission on the target project
- `Error 409: The requested bucket name is not available` → globally unique GCS name is taken; the contributor needs to rename in `gcs.tf`
- `Error: Failed to get existing workspaces: storage: bucket doesn't exist` → backend bucket `dark-tfstates` is missing or the contributor doesn't have read access

After a successful plan, parse the trailing summary line:

```
Plan: <add> to add, <change> to change, <destroy> to destroy.
```

Surface this to the contributor along with the high-level resource list (resource type and name only, not full diffs — those are in `tfplan.out` if they want to inspect with `terraform show tfplan.out`).

If the action was **Plan only**, jump straight to Step 8 with `applied = false`.

---

### Step 7 — Gate 2: Execute

Use `AskUserQuestion`:

> Plan: `<add>` to add, `<change>` to change, `<destroy>` to destroy.
>
> Resources affected:
> - `<list>`
>
> Apply this plan?
>
> Options:
> - Apply
> - Show full diff first (run `terraform show tfplan.out` and re-ask)
> - Cancel

If **Show full diff**, run `terraform show -no-color tfplan.out`, surface the output, and re-issue the same gate question (without the "Show full diff" option this time).

If **Cancel**, exit cleanly. The `tfplan.out` file remains on disk; the contributor can apply it manually later if they change their mind.

If **Apply**, fire:

```bash
terraform apply -input=false tfplan.out
```

If apply fails (e.g. mid-apply API error, name conflict that wasn't caught at plan, lock contention, etc.), surface the full error and **stop**. Do not retry automatically. Common causes:

- `Error acquiring the state lock` → another `apply` is running, or a previous one crashed and left the lock. Surface the lock ID and tell the contributor to run `terraform force-unlock <ID>` manually if they're sure no other apply is running.
- `Error 409: ... bucket namespace is shared by all users` → name conflict at create time (rare if plan was clean — usually means a race with another GCS user). Tell the contributor to rename and re-plan.
- Partial-apply errors (some resources created, others failed) leave the state inconsistent. **Do not auto-rollback**. Surface the full apply log and let the contributor decide whether to fix forward (edit `.tf`, re-plan, re-apply) or roll back manually.

---

### Step 8 — Report

Print:

- Action taken (apply / destroy / plan-only)
- Plan summary (`<add>` / `<change>` / `<destroy>` counts)
- Whether apply ran and whether it succeeded
- Outputs (run `terraform output` if any are defined; skip otherwise)
- State location (parse from the backend block in [terraform/terraform.tf](../../../terraform/terraform.tf), e.g. `gs://dark-tfstates/rentals-data-pipeline/state/default.tfstate`)
- Cleanup hint: `tfplan.out` is left on disk and gitignored; the contributor can delete it (`rm tfplan.out`) once they're done

If the contributor's action was **Plan only**, also tell them:

> The saved plan is at `tfplan.out`. To apply it later: `terraform apply tfplan.out` from inside `terraform/`. Note: a plan file goes stale when the underlying GCP state drifts — re-plan if much time has passed.

---

## Error Handling Principles

- **Never skip a failed step silently** — surface the full Terraform/gcloud error and stop.
- **Diagnose before retrying** — read the error message and translate it for the contributor (auth issue? name conflict? missing API? lock contention?).
- **Halt on first failure** — per the project's preference, don't muscle through partial failures.
- **The contributor authors infra; the skill executes it** — never edit `.tf` files to "fix" a validation or plan error. Surface and stop.
- **Saved plan files are the contract** — once the contributor approves a plan at gate 2, apply that exact saved plan, not a fresh re-plan.

## Refusal triggers

The skill must refuse and explain when:

- `terraform` CLI is not installed.
- `terraform/` directory is missing.
- Application Default Credentials are not set or `gcloud auth application-default print-access-token` fails.
- `terraform init` would migrate or reconfigure the backend.
- `terraform validate` fails — the contributor must fix the `.tf` files first.
- `terraform plan` fails — surface the full error and stop.
- `terraform apply` fails — surface the full error and stop; do not auto-rollback.
- The contributor declines at any gate.
- The contributor asks the skill to bootstrap GCP projects, billing, APIs, or the state bucket — those are out of scope; redirect to [terraform/README.md](../../../terraform/README.md) Prerequisites.
