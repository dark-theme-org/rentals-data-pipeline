"""Generic enums, credential resolution, and logging setup shared across the app."""

import logging
import os
from enum import StrEnum
from pathlib import Path

import google.auth
from google.auth import impersonated_credentials
from google.auth.credentials import Credentials

PROJECT_ID: str = (Path(__file__).parents[3] / ".google-project-id").read_text().strip()


class Environment(StrEnum):
    """Supported deployment environments for the data pipeline."""

    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class FileExtensions(StrEnum):
    """Supported file extensions for blob storage payloads."""

    JSON = "json"


class ServiceAccountNames(StrEnum):
    """Env var names `get_credentials` reads to pick which service account to impersonate."""

    GCS = "GCS_SA"


def configure_logging(level: int = logging.INFO) -> None:
    """
    Attach a StreamHandler to the root logger with a uniform format so that
    `logger.info(...)` calls from app code surface in the terminal.
    Idempotent: ``logging.basicConfig`` is a no-op when a handler is already
    configured, so calling it again (e.g. from tests, REPL re-imports) won't
    duplicate output.

    Call this once per entrypoint, inside the ``if __name__ == "__main__":``
    block (before invoking the @task-decorated function) so the wrapper's
    "Starting task execution" log line is visible.

    ----------
    Parameters
    ----------
    level : int, default logging.INFO
        Threshold for the root logger; messages below this level are dropped.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] - %(message)s",
    )


def get_credentials(env_var: str) -> Credentials:
    """
    Resolve credentials for Google Cloud clients across local-dev and
    attached-SA runtime contexts.

    If ``env_var`` is set in the environment, impersonate the service
    account named in that variable on top of the default Application
    Default Credentials — the expected local-development path where the
    developer's user account holds ``roles/iam.serviceAccountTokenCreator``
    on the target SA. Different callers can use different env vars
    (e.g. ``GCS_SA``, ``BQ_SA``) when they need to act as different SAs.

    If ``env_var`` is unset, return the default ADC unchanged. In
    attached-SA runtimes (Cloud Run, Cloud Workflows, GCE), this resolves
    to the runtime's own service account via the metadata server with no
    extra configuration.

    ----------
    Parameters
    ----------
    env_var : str
        Name of the environment variable that, when set, holds the email
        of the service account to impersonate.

    ----------
    Returns
    ----------
    Credentials
        Credentials object to pass to ``<gcp-client>.Client(credentials=...)``.
    """
    base_creds, _ = google.auth.default()
    target_sa = os.environ.get(env_var)
    if not target_sa:
        return base_creds
    return impersonated_credentials.Credentials(  # type: ignore[no-untyped-call]
        source_credentials=base_creds,
        target_principal=target_sa,
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
