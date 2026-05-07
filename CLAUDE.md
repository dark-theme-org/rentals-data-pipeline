# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
name: Skill name                                      # Must match folder name
description: When to invoke this skill                # Recommended action
disable-model-invocation: false                       # Allow auto-invocation if relevant
user-invocable: true                                  # Show in / menu
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
  - Runs `pyenv install`, `poetry install`, `commands/setup_lab.sh` and `poetry shell`
  - Validates each step before proceeding and surfaces errors clearly

### Creating New Skills

To create a new skill:

1. Create directory: `.claude/skills/<name>/`
2. Create file: `.claude/skills/<name>/SKILL.md` with YAML frontmatter and instructions
3. The skill will be automatically available as `/skill-name`
4. Add documentation here when the skill is ready

---
