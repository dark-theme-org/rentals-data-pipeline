"""Generic enums shared across the app."""

from enum import StrEnum


class Environment(StrEnum):
    """Supported deployment environments for the data pipeline."""

    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class FileExtensions(StrEnum):
    """Supported file extensions for blob storage payloads."""

    JSON = "json"
