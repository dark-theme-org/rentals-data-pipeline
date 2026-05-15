"""Deploy Cloud Run Jobs and Cloud Workflows from cloud/ YAML definitions."""

import argparse
import subprocess  # nosec
import sys
from pathlib import Path
from typing import Any

import yaml

_cloud_dir = Path(__file__).parent.parent / "cloud"
TASKS_DIR = _cloud_dir / "tasks"
WORKFLOWS_DIR = _cloud_dir / "workflows"

_settings: dict = yaml.safe_load((_cloud_dir / "settings.yml").read_text(encoding="utf-8"))
PROJECT_ID: str = _settings["project_id"]
REGION: str = _settings["region"]

AR_REPO: str = f"{PROJECT_ID}-docker"
IMAGE_URL: str = f"{REGION}-docker.pkg.dev/{PROJECT_ID}/{AR_REPO}/{{task_name}}:{{version}}"
SA_EMAIL: str = f"{PROJECT_ID}-sa@{PROJECT_ID}.iam.gserviceaccount.com"


def run_cmd(cmd: list[str], step: str) -> None:
    """
    Run a subprocess command and exit with a named step error on failure.

    ----------
    Parameters
    ----------
    cmd : list[str]
        Command and arguments to execute.
    step : str
        Step label shown in the error message.

    ----------
    Raises
    ----------
    SystemExit
        If the command exits with a non-zero return code.
    """
    result = subprocess.run(cmd, capture_output=True, text=True)  # pylint: disable=W1510  # nosec
    if result.returncode != 0:
        print(f"ERROR [{step}]:\n{result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)


def build_and_push_images(task_name: str, version: str) -> None:
    """
    Build and push the Docker image for a task to Artifact Registry.

    ----------
    Parameters
    ----------
    task_name : str
        Task name used as the ``TASK_NAME`` build arg and image name.
    version : str
        Docker image tag to apply.
    """
    url = IMAGE_URL.format(task_name=task_name, version=version)
    run_cmd(
        ["docker", "build", "--build-arg", f"TASK_NAME={task_name}", "-t", url, "."],
        f"build:{task_name}",
    )
    run_cmd(["docker", "push", url], f"push:{task_name}")


def deploy_task(
    name: str,
    configs: dict[str, Any],
    version: str,
    params_override: dict[str, str] | None = None,
) -> None:
    """
    Create the Cloud Run Job for a task from its YAML definition.

    ----------
    Parameters
    ----------
    name : str
        Task name; used to derive the job name (``_`` replaced by ``-``).
    configs : dict[str, Any]
        Parsed task YAML configs containing ``machine``, ``retry``, and ``inputs``.
    version : str
        Docker image tag the job will run.
    params_override : dict[str, str] | None
        Optional parameter overrides that take precedence over YAML defaults.
    """
    url = IMAGE_URL.format(task_name=name, version=version)
    params = {p["name"]: str(p["default"]) for p in configs.get("inputs", {}).get("parameters", [])}
    if params_override:
        params.update(params_override)
    env_vars = "^|^" + "|".join([f"TASK_NAME={name}"] + [f"{k}={v}" for k, v in params.items()])
    run_cmd(
        [
            "gcloud",
            "run",
            "jobs",
            "create",
            name.replace("_", "-"),
            "--image",
            url,
            "--region",
            REGION,
            "--service-account",
            SA_EMAIL,
            "--memory",
            configs["machine"]["memory"],
            "--cpu",
            str(configs["machine"]["cpu"]),
            "--task-timeout",
            configs["machine"]["timeout"],
            "--max-retries",
            str(configs.get("retry", {}).get("repetitions", 0)),
            "--set-env-vars",
            env_vars,
            "--project",
            PROJECT_ID,
            "--quiet",
        ],
        f"deploy:{name}",
    )


def run_workflow(name: str, file: Path) -> None:
    """
    Run a Cloud Workflow from its YAML definition.

    ----------
    Parameters
    ----------
    name : str
        Workflow name; used to derive the Cloud Workflows resource name (``_`` → ``-``).
    file : Path
        Path to the Cloud Workflows YAML source file.
    """
    run_cmd(
        [
            "gcloud",
            "workflows",
            "deploy",
            name.replace("_", "-"),
            "--location",
            REGION,
            "--source",
            str(file),
            "--service-account",
            SA_EMAIL,
            "--project",
            PROJECT_ID,
            "--quiet",
        ],
        f"run:{name}",
    )


def main() -> None:
    """Parse arguments and execute the requested deploy steps."""
    # 1. Parse declared arguments during script invoke
    parser = argparse.ArgumentParser(
        description="Deploy Cloud Run Jobs and Cloud Workflows from cloud/ YAML definitions."
    )
    parser.add_argument("--version", required=True, help="Docker image tag version.")
    parser.add_argument(
        "--tasks",
        nargs="+",
        default=None,
        metavar="TASK_NAME",
        help="Named task(s) for build/push process. All if omitted.",
    )
    parser.add_argument("--skip-build", action="store_true", help="Skip docker build and push.")
    parser.add_argument("--skip-deploy", action="store_true", help="Skip Cloud Run Job creation.")
    parser.add_argument(
        "--params",
        nargs="+",
        default=None,
        metavar="KEY=VALUE",
        help="Override task parameter values.",
    )
    parser.add_argument("--skip-run", action="store_true", help="Skip Cloud Workflow deployment.")
    parser.add_argument(
        "--workflow",
        default=None,
        help="Named workflow to run. Will run all if omitted.",
    )
    args = parser.parse_args()
    # 2. Execute each mandatory step sequentially:
    # 2.1. Build/Push task images -> deploy tasks
    task_files = sorted(TASKS_DIR.glob("*.yml"))
    if args.tasks:
        available_tasks = [f.stem for f in task_files]
        unknown = [t for t in args.tasks if t not in available_tasks]
        if unknown:
            print(
                f"ERROR: Unknown task(s): {unknown}. Availables: {available_tasks}", file=sys.stderr
            )
            sys.exit(1)
        task_files = [f for f in task_files if f.stem in args.tasks]
    for task_file in task_files:
        task_name = task_file.stem
        task_configs = yaml.safe_load(task_file.read_text(encoding="utf-8"))
        if not args.skip_build:
            build_and_push_images(task_name, args.version)
        if not args.skip_deploy:
            params_override: dict[str, str] | None = (
                {k: v for kv in args.params for k, _, v in [kv.partition("=")]}
                if args.params
                else None
            )
            deploy_task(task_name, task_configs, args.version, params_override)
    # 2.2. Run workflow
    if not args.skip_run:
        workflow_files = sorted(WORKFLOWS_DIR.glob("*.yml"))
        if args.workflow:
            available_workflows = [f.stem for f in workflow_files]
            if args.workflow not in available_workflows:
                print(
                    f"ERROR: Unknown workflow '{args.workflow}'. Availables: {available_workflows}",
                    file=sys.stderr,
                )
                sys.exit(1)
            workflow_files = [f for f in workflow_files if f.stem == args.workflow]
        for workflow_file in workflow_files:
            run_workflow(workflow_file.stem, workflow_file)


if __name__ == "__main__":
    main()
