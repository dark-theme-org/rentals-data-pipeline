"""Deploy Cloud Run Jobs and Cloud Workflows from cloud/ YAML definitions."""

import argparse
import json
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


def _versioned_name(name: str, version: str) -> str:
    """Return a GCP-safe resource name with the version appended."""
    return f"{name.replace('_', '-')}-{version.replace('.', '-')}"


def run_cmd(cmd: list[str], step: str, env: dict | None = None) -> None:
    """
    Run a subprocess command and exit with a named step error on failure.

    ----------
    Parameters
    ----------
    cmd : list[str]
        Command and arguments to execute.
    step : str
        Step label shown in the error message.
    env : dict | None
        Optional environment variables for the subprocess. Defaults to the
        current process environment when ``None``.

    ----------
    Raises
    ----------
    SystemExit
        If the command exits with a non-zero return code.
    """
    result = subprocess.run(  # pylint: disable=W1510  # nosec
        cmd, capture_output=True, text=True, env=env
    )
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
        [
            "docker",
            "buildx",
            "build",
            "--platform",
            "linux/amd64",
            "--provenance",
            "false",
            "--sbom",
            "false",
            "--build-arg",
            f"TASK_NAME={task_name}",
            "-t",
            url,
            "--push",
            ".",
        ],
        f"build:{task_name}",
    )


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
            _versioned_name(name, version),
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


def deploy_workflow(name: str, file: Path, version: str) -> None:
    """
    Upload a Cloud Workflow definition to GCP from its YAML source.

    ----------
    Parameters
    ----------
    name : str
        Workflow name; used to derive the Cloud Workflows resource name (``_`` → ``-``).
    file : Path
        Path to the Cloud Workflows YAML source file.
    version : str
        Version tag appended to the workflow resource name.
    """
    run_cmd(
        [
            "gcloud",
            "workflows",
            "deploy",
            _versioned_name(name, version),
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
        f"deploy-workflow:{name}",
    )


def run_workflow(name: str, version: str, params: dict[str, str] | None = None) -> None:
    """
    Trigger a Cloud Workflow execution.

    ----------
    Parameters
    ----------
    name : str
        Workflow name; used to derive the Cloud Workflows resource name (``_`` → ``-``).
    version : str
        Version tag used to resolve the versioned workflow and job names.
    params : dict[str, str] | None
        Optional input parameters passed as workflow arguments. Keys are
        uppercased before being serialised to JSON.
    """
    data: dict[str, str] = {k.upper(): v for k, v in (params or {}).items()}
    data["VERSION"] = version.replace(".", "-")
    run_cmd(
        [
            "gcloud",
            "workflows",
            "run",
            _versioned_name(name, version),
            "--location",
            REGION,
            "--project",
            PROJECT_ID,
            "--data",
            json.dumps(data),
        ],
        f"run-workflow:{name}",
    )


def main() -> None:
    """Parse arguments and execute the requested deploy steps."""
    parser = argparse.ArgumentParser(
        description="Deploy Cloud Run Jobs and Cloud Workflows from cloud/ YAML definitions."
    )
    parser.add_argument("--version", required=True, help="Docker image tag version.")
    parser.add_argument(
        "--tasks",
        nargs="+",
        default=None,
        metavar="TASK_NAME",
        help="Named task(s) for build/deploy process. All if omitted.",
    )
    parser.add_argument("--skip-build", action="store_true", help="Skip docker build and push.")
    parser.add_argument(
        "--skip-task-deploy", action="store_true", help="Skip Cloud Run Job creation."
    )
    parser.add_argument(
        "--params",
        nargs="+",
        default=None,
        metavar="KEY=VALUE",
        help="Override task parameter values and workflow execution inputs.",
    )
    parser.add_argument(
        "--workflow",
        default=None,
        help="Named workflow to deploy/run. All if omitted.",
    )
    parser.add_argument(
        "--skip-workflow-deploy", action="store_true", help="Skip Cloud Workflow definition upload."
    )
    parser.add_argument(
        "--skip-workflow-run", action="store_true", help="Skip Cloud Workflow execution trigger."
    )
    args = parser.parse_args()

    params_override: dict[str, str] | None = (
        {k: v for kv in args.params for k, _, v in [kv.partition("=")]} if args.params else None
    )

    # Step 1: Build/push images and deploy Cloud Run Jobs
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
        if not args.skip_task_deploy:
            deploy_task(task_name, task_configs, args.version, params_override)

    # Step 2: Deploy and run Cloud Workflows
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
        if not args.skip_workflow_deploy:
            deploy_workflow(workflow_file.stem, workflow_file, args.version)
        if not args.skip_workflow_run:
            workflow_params: dict[str, str] = {}
            for task_file in sorted(TASKS_DIR.glob("*.yml")):
                task_configs = yaml.safe_load(task_file.read_text(encoding="utf-8"))
                workflow_params.update(
                    {
                        p["name"]: str(p["default"])
                        for p in task_configs.get("inputs", {}).get("parameters", [])
                    }
                )
            if params_override:
                workflow_params.update(params_override)
            run_workflow(workflow_file.stem, args.version, workflow_params)


if __name__ == "__main__":
    main()
