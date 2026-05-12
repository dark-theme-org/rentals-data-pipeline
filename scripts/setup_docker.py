"""Docker entrypoint: Reads tasks.yml and execs the configured task command."""

import os
import sys
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

TASK_NAME_DOCKER_PARAM = "TASK_NAME"
TASKS_FILE = Path(__file__).parent.parent / "tasks.yml"


class OperatorTypes(StrEnum):
    """Supported operator types for task execution."""

    BASH = "bash"
    PYTHON = "python"


def build_cmd(task: dict[str, Any]) -> list[str]:
    """
    Build the exec command list from the task type and entrypoint.

    ----------
    Parameters
    ----------
    task : dict[str, Any]
        Task configuration dict loaded from tasks.yml. Must contain
        ``type`` (one of :class:`OperatorTypes`) and ``entrypoint``
        (module path or script path).

    ----------
    Returns
    ----------
    list[str]
        Command and arguments passed to :func:`os.execvpe`.

    ----------
    Raises
    ----------
    SystemExit
        If ``task["type"]`` is not one of the supported operator types.
        The error message includes the full list of available types.
    """
    op_type, entrypoint = task["type"], task["entrypoint"]
    if op_type == OperatorTypes.PYTHON:
        return [OperatorTypes.PYTHON, "-m", entrypoint]
    if op_type == OperatorTypes.BASH:
        return [OperatorTypes.BASH, entrypoint]
    sys.exit(
        f"ERROR: Unknown task type '{op_type}'. " f"Availables: {[e.value for e in OperatorTypes]}"
    )


def main() -> None:
    """Load the task config, inject parameter defaults, and exec the task command."""
    task_name = os.environ.get(TASK_NAME_DOCKER_PARAM)
    if not task_name:
        sys.exit(f"ERROR: Parameter '{TASK_NAME_DOCKER_PARAM}' is not set.")
    with open(TASKS_FILE, encoding="utf-8") as f:
        tasks = yaml.safe_load(f)
    task = tasks.get(task_name)
    if task is None:
        sys.exit(f"ERROR: Task '{task_name}' not found in yml. Availables: {list(tasks.keys())}")
    for param in task.get("inputs", {}).get("parameters", []):
        os.environ.setdefault(param["name"].upper(), str(param["default"]))
    cmd = build_cmd(task)
    print(f"Running task '{task_name}'", flush=True)
    os.execvpe(cmd[0], cmd, os.environ)  # nosec


if __name__ == "__main__":
    main()
