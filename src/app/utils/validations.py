"""Runtime input parameter validation for pipeline tasks."""

import dataclasses
import logging
import os
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.data.scrapers import City, VivaRealScraper, ZapImoveisScraper
from app.data.scrapers.settings import PropertyTypes
from app.utils.utils import Environment, FileExtensions, datetime_now_utc

logger = logging.getLogger(__name__)

_VALID_CITIES: list[str] = [city.value for city in City]
_VALID_ENVIRONMENTS: list[str] = [env.value for env in Environment]
_VALID_PROPERTY_TYPES: list[str] = [f.name for f in dataclasses.fields(PropertyTypes)]
_VALID_SITES: list[str] = [
    VivaRealScraper.get_site_name(),
    ZapImoveisScraper.get_site_name(),
]


class InputParameters(BaseModel):
    """
    Base model with shared fields and validation logic for all pipeline tasks.

    Subclasses inherit ``environment``, ``city``, ``sites``, ``property_types``,
    and ``version`` together with their validators. Task-specific fields and
    ``from_env`` are defined in each subclass.
    """

    environment: str = Field(strict=True)
    city: str = Field(strict=True)
    sites: list[str] = Field(strict=True)
    property_types: list[str] = Field(strict=True)
    version: str
    start_page: int
    max_page: int | None
    executed_at: str = datetime_now_utc()
    file_extension: str = FileExtensions.JSON.value

    @classmethod
    def _base_env(cls) -> dict:
        """Read the env vars shared across all pipeline tasks."""
        return {
            "environment": os.environ["ENVIRONMENT"],
            "city": os.environ["CITY"],
            "sites": os.environ["SITES"],
            "property_types": os.environ["PROPERTY_TYPES"],
            "version": os.environ.get("VERSION", "unknown"),
            "start_page": os.environ["START_PAGE"],
            "max_page": os.environ["MAX_PAGE"] if int(os.environ["MAX_PAGE"]) > 0 else None,
        }

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, input_value: str) -> str:
        """
        Validate that 'environment' is one of the available environments.

        ----------
        Parameters
        ----------
        input_value : str
            Declared 'environment' parameter.

        ----------
        Returns
        ----------
        str
            Value as-expected if valid. Else, raises ValueError with available options.
        """
        v = input_value.strip().lower()
        if v not in _VALID_ENVIRONMENTS:
            raise ValueError(f"must be one of the available environments: {_VALID_ENVIRONMENTS}.")
        return v

    @field_validator("city")
    @classmethod
    def validate_city(cls, input_value: str) -> str:
        """
        Validate that 'city' is one of the available cities.

        ----------
        Parameters
        ----------
        input_value : str
            Declared 'city' parameter.

        ----------
        Returns
        ----------
        str
            Value as-expected if valid. Else, raises ValueError with available options.
        """
        v = input_value.strip().lower()
        if v not in _VALID_CITIES:
            raise ValueError(f"must be one of the available cities: {_VALID_CITIES}.")
        return v

    @field_validator("sites", mode="before")
    @classmethod
    def validate_sites(cls, input_value: str) -> list[str]:
        """
        Validate each site against available scrapers and parse the comma-separated string.

        ----------
        Parameters
        ----------
        input_value : str
            Declared 'sites' parameter as a comma-separated string.

        ----------
        Returns
        ----------
        list[str]
            List of site slugs if all are valid. Else, raises ValueError with available options.
        """
        sites = [s.strip().lower() for s in input_value.split(",")]
        for site in sites:
            if site not in _VALID_SITES:
                raise ValueError(f"'{site}' is not valid. Available sites: {_VALID_SITES}.")
        return sites

    @field_validator("property_types", mode="before")
    @classmethod
    def validate_property_types(cls, input_value: str) -> list[str]:
        """
        Validate each property type and parse the comma-separated string.

        ----------
        Parameters
        ----------
        input_value : str
            Declared 'property_types' parameter as a comma-separated string.

        ----------
        Returns
        ----------
        list[str]
            List of property type slugs if all are valid.
            Else, raises ValueError with available options.
        """
        types = [pt.strip().lower() for pt in input_value.split(",")]
        for pt in types:
            if pt not in _VALID_PROPERTY_TYPES:
                raise ValueError(
                    f"'{pt}' is not valid. Available property types: {_VALID_PROPERTY_TYPES}."
                )
        return types


class ScraperParameters(InputParameters):
    """Validates and parses input parameters for the scraper_data_to_bucket task."""

    upload_to_gcs: bool
    max_long_retries: int = 3

    @classmethod
    def from_env(cls) -> "ScraperParameters":
        """Instantiate by reading the required environment variables."""
        return cls.model_validate({**cls._base_env(), "upload_to_gcs": os.environ["UPLOAD_TO_GCS"]})


class BronzeParameters(InputParameters):
    """Validates and parses input parameters for the gcs_to_bigquery_bronze task."""

    upload_to_bq: bool
    file_date: str = Field(strict=True)

    @classmethod
    def from_env(cls) -> "BronzeParameters":
        """Instantiate by reading the required environment variables."""
        return cls.model_validate(
            {
                **cls._base_env(),
                "upload_to_bq": os.environ["UPLOAD_TO_BQ"],
                "file_date": os.environ.get("FILE_DATE") or datetime_now_utc(date_trunc=True),
            }
        )

    @field_validator("file_date")
    @classmethod
    def validate_file_date(cls, input_value: str) -> str:
        """
        Validate that 'file_date' is a non-empty date string in YYYY-MM-DD format.

        ----------
        Parameters
        ----------
        input_value : str
            Declared 'file_date' parameter.

        ----------
        Returns
        ----------
        str
            Value as-expected if valid. Else, raises ValueError with expected format.
        """
        try:
            datetime.strptime(input_value, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(
                f"'{input_value}' is not a valid `file_date`. Expected format: 'YYYY-MM-DD'."
            ) from exc
        return input_value
