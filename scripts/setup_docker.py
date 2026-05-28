"""Docker entrypoint: Reads tasks.yml and execs the configured task command."""

import os
import shlex
import sys
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

TASK_NAME_DOCKER_PARAM = "TASK_NAME"
CLOUD_DIR = Path(__file__).parent.parent / "cloud"


class OperatorTypes(StrEnum):
    """Supported operator types for task execution."""

    DBT = "dbt"
    PYTHON = "python"


def build_cmd(task: dict[str, Any]) -> list[str]:
    """
    Build the exec command list from the task type and entrypoint.

    ----------
    Parameters
    ----------
    task : dict[str, Any]
        Task configuration dict loaded from tasks.yml. Must contain
        ``type`` (one of :class:`OperatorTypes`) and ``entrypoint``.
        For ``python``: a dotted module path (e.g. ``app.entrypoints.scraper_data_to_bucket``).
        For ``dbt``: the dbt sub-command and flags as a single string
        (e.g. ``run --profiles-dir dbt --project-dir dbt --select silver``).

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
    if op_type == OperatorTypes.DBT:
        cmd = [OperatorTypes.DBT] + shlex.split(entrypoint)
        if target := os.environ.get("ENVIRONMENT"):
            cmd += ["--target", target]
        return cmd
    sys.exit(
        f"ERROR: Unknown task type '{op_type}'. " f"Availables: {[e.value for e in OperatorTypes]}"
    )


def main() -> None:
    """Load the task config, inject parameter defaults and project settings, then exec the task."""
    task_name = os.environ.get(TASK_NAME_DOCKER_PARAM)
    if not task_name:
        sys.exit(f"ERROR: Parameter '{TASK_NAME_DOCKER_PARAM}' is not set.")
    task_file = CLOUD_DIR / "tasks" / f"{task_name}.yml"
    if not task_file.exists():
        available = [f.stem for f in (CLOUD_DIR / "tasks").glob("*.yml")]
        sys.exit(f"ERROR: Task '{task_name}' not found. Availables: {available}")
    settings = yaml.safe_load((CLOUD_DIR / "settings.yml").read_text(encoding="utf-8"))
    os.environ.setdefault("PROJECT_ID", settings["project_id"])
    os.environ.setdefault("LOCATION", settings["location"])
    with open(task_file, encoding="utf-8") as f:
        task = yaml.safe_load(f)
    for param in task.get("inputs", {}).get("parameters", []):
        os.environ.setdefault(param["name"].upper(), str(param["default"]))
    cmd = build_cmd(task)
    print(f"Running task '{task_name}'", flush=True)
    os.execvpe(cmd[0], cmd, os.environ)  # nosec


if __name__ == "__main__":
    main()
