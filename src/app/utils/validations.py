"""Runtime input parameter validation for pipeline tasks."""

import dataclasses
import logging
import os
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

from app.data.scrapers import City, VivaRealScraper, ZapImoveisScraper
from app.data.scrapers.settings import PropertyTypes
from app.utils.utils import Environment, FileExtensions, ServiceAccountNames

logger = logging.getLogger(__name__)

_VALID_CITIES: list[str] = [city.value for city in City]
_VALID_ENVIRONMENTS: list[str] = [env.value for env in Environment]
_VALID_PROPERTY_TYPES: list[str] = [f.name for f in dataclasses.fields(PropertyTypes)]
_VALID_SITES: list[str] = [
    VivaRealScraper.get_site_name(),
    ZapImoveisScraper.get_site_name(),
]


class InputParameters(BaseModel):
    """Base class for runtime task input parameter validation."""


class ScraperParameters(InputParameters):
    """Validates and parses input parameters for the scraper_data_to_bucket task."""

    environment: str = Field(strict=True)
    city: str = Field(strict=True)
    sites: list[str] = Field(strict=True)
    property_types: list[str] = Field(strict=True)
    upload_to_gcs: bool
    start_page: int
    max_page: int | None
    version: str
    executed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    )
    max_long_retries: int = 3
    file_extension: str = FileExtensions.JSON.value
    sa_name: str = ServiceAccountNames.GCS.value

    @classmethod
    def from_env(cls) -> "ScraperParameters":
        """Instantiate by reading the required environment variables."""
        return cls.model_validate(
            {
                "environment": os.environ["ENVIRONMENT"],
                "city": os.environ["CITY"],
                "sites": os.environ["SITES"],
                "property_types": os.environ["PROPERTY_TYPES"],
                "upload_to_gcs": os.environ["UPLOAD_TO_GCS"],
                "start_page": os.environ["START_PAGE"],
                "max_page": os.environ["MAX_PAGE"] if int(os.environ["MAX_PAGE"]) > 0 else None,
                "version": os.environ.get("VERSION", "unknown"),
            }
        )

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
        env_value = input_value.strip().lower()
        if env_value not in _VALID_ENVIRONMENTS:
            raise ValueError(f"must be one of the available environments: {_VALID_ENVIRONMENTS}.")
        return env_value

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
        city_value = input_value.strip().lower()
        if city_value not in _VALID_CITIES:
            raise ValueError(f"must be one of the available cities: {_VALID_CITIES}.")
        return city_value

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
        sites_list = [s.strip().lower() for s in input_value.split(",")]
        for site in sites_list:
            if site not in _VALID_SITES:
                raise ValueError(f"'{site}' is not valid. Available sites: {_VALID_SITES}.")
        return sites_list

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
        property_types_list = [pt.strip().lower() for pt in input_value.split(",")]
        for property_type in property_types_list:
            if property_type not in _VALID_PROPERTY_TYPES:
                raise ValueError(
                    f"'{property_type}' is not valid. "
                    f"Available property types: {_VALID_PROPERTY_TYPES}."
                )
        return property_types_list
