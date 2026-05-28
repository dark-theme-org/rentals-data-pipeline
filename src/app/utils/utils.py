"""Generic enums, credential resolution, and logging setup shared across the app."""

import logging
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

import google.auth
import yaml
from google.auth.credentials import Credentials

_SETTINGS: dict = yaml.safe_load(
    (Path(__file__).parents[3] / "cloud" / "settings.yml").read_text(encoding="utf-8")
)
_SETTINGS_ENVS: dict = _SETTINGS["environments"]


class Environment(StrEnum):
    """Supported deployment environments for the data pipeline."""

    DEV = _SETTINGS_ENVS["dev"]
    TEST = _SETTINGS_ENVS["test"]
    PROD = _SETTINGS_ENVS["prod"]


class FileExtensions(StrEnum):
    """Supported file extensions for blob storage payloads."""

    JSON = "json"


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


def datetime_now_utc(date_trunc: bool = False) -> str:
    """
    Return the current UTC time as a formatted string.

    ----------
    Parameters
    ----------
    date_trunc : bool, default False
        If True, return only the date portion (``YYYY-MM-DD``).
        If False, return the full ISO-8601 datetime (``YYYY-MM-DDTHH:MM:SSZ``).

    ----------
    Returns
    ----------
    str
        Formatted UTC datetime or date string.
    """
    now = datetime.now(timezone.utc)
    if date_trunc:
        return now.strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_credentials() -> Credentials:
    """
    Resolve credentials for Google Cloud clients.

    Returns ADC credentials directly. In Cloud Run, resolves to the runtime
    SA via the metadata server. Locally, resolves to whatever credentials are
    configured via ``gcloud auth application-default login`` — use
    ``--impersonate-service-account`` to mirror the Cloud Run SA permissions.

    ----------
    Returns
    ----------
    Credentials
        Credentials object to pass to ``<gcp-client>.Client(credentials=...)``.
    """
    creds, _ = google.auth.default()
    return creds
