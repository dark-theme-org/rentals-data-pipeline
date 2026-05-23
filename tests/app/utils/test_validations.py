"""Tests for ScraperParameters and BronzeParameters input validation."""

import os
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.utils.validations import BronzeParameters, ScraperParameters

_default_env = {
    "environment": os.environ["ENVIRONMENT"],
    "city": os.environ["CITY"],
    "sites": os.environ["SITES"],
    "property_types": os.environ["PROPERTY_TYPES"],
    "start_page": os.environ["START_PAGE"],
    "max_page": os.environ["MAX_PAGE"],
    "version": os.environ.get("VERSION", "unknown"),
}


@pytest.fixture(name="valid_scraper_env")
def valid_scraper_env_() -> dict:
    """Raw env-var string dict mirroring pytest.ini values for ScraperParameters tests."""
    return {
        **_default_env,
        "upload_to_gcs": os.environ["UPLOAD_TO_GCS"],
    }


@pytest.fixture(name="valid_bronze_env")
def valid_bronze_env_() -> dict:
    """Field dict mirroring pytest.ini values for BronzeParameters tests."""
    return {
        **_default_env,
        "file_date": os.environ["FILE_DATE"],
        "upload_to_bq": os.environ["UPLOAD_TO_BQ"],
    }


# ---------------------------------------------------------------------------
# ScraperParameters
# ---------------------------------------------------------------------------


def test_from_env_success(env: str, expected_city: str, valid_scraper_env: dict) -> None:
    """Test from_env returns a valid ScraperParameters from environment variables."""
    params = ScraperParameters.from_env()
    assert params.environment == env
    assert params.city == expected_city
    assert params.sites == [s.strip().lower() for s in valid_scraper_env["sites"].split(",")]
    assert params.property_types == [
        pt.strip().lower() for pt in valid_scraper_env["property_types"].split(",")
    ]
    assert params.upload_to_gcs is (valid_scraper_env["upload_to_gcs"].lower() == "true")
    assert params.start_page == int(valid_scraper_env["start_page"])
    if int(valid_scraper_env["max_page"]) <= 0:
        assert params.max_page is None
    else:
        assert params.max_page == int(valid_scraper_env["max_page"])


def test_from_env_raises_on_missing_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test from_env raises KeyError when a required environment variable is absent."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    with pytest.raises(KeyError):
        ScraperParameters.from_env()


def test_validate_environment_raises_on_invalid_value(valid_scraper_env: dict) -> None:
    """Test validate_environment raises ValidationError for an unsupported environment."""
    with pytest.raises(ValidationError, match="available environments"):
        ScraperParameters.model_validate({**valid_scraper_env, "environment": "staging"})


def test_validate_city_raises_on_invalid_value(valid_scraper_env: dict) -> None:
    """Test validate_city raises ValidationError for an unsupported city."""
    with pytest.raises(ValidationError, match="available cities"):
        ScraperParameters.model_validate({**valid_scraper_env, "city": "rio"})


def test_validate_sites_raises_on_unknown_site(valid_scraper_env: dict) -> None:
    """Test validate_sites raises ValidationError when a site slug is not registered."""
    with pytest.raises(ValidationError, match="not valid"):
        ScraperParameters.model_validate({**valid_scraper_env, "sites": "vivareal,unknown"})


def test_validate_sites_normalises_csv_input(valid_scraper_env: dict) -> None:
    """Test validate_sites strips whitespace and lowercases each site slug."""
    params = ScraperParameters.model_validate(
        {**valid_scraper_env, "sites": " VivaReal , ZapImoveis "}
    )
    assert params.sites == ["vivareal", "zapimoveis"]


def test_validate_property_types_raises_on_unknown_type(valid_scraper_env: dict) -> None:
    """Test validate_property_types raises ValidationError for an unsupported property type."""
    with pytest.raises(ValidationError, match="not valid"):
        ScraperParameters.model_validate({**valid_scraper_env, "property_types": "studio"})


def test_validate_property_types_normalises_csv_input(valid_scraper_env: dict) -> None:
    """Test validate_property_types strips whitespace and lowercases each type."""
    params = ScraperParameters.model_validate(
        {**valid_scraper_env, "property_types": " Apartment , House "}
    )
    assert params.property_types == ["apartment", "house"]


def test_from_env_upload_to_gcs_false_string_parsed_as_bool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test from_env coerces UPLOAD_TO_GCS="false" to bool False via Pydantic lax validation."""
    monkeypatch.setenv("UPLOAD_TO_GCS", "false")
    params = ScraperParameters.from_env()
    assert params.upload_to_gcs is False


def test_from_env_upload_to_gcs_capital_true_parsed_as_bool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test from_env coerces UPLOAD_TO_GCS="True" (str(True) from setup_docker.py) to bool True."""
    monkeypatch.setenv("UPLOAD_TO_GCS", "True")
    params = ScraperParameters.from_env()
    assert params.upload_to_gcs is True


def test_from_env_start_page_parsed_as_int(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test from_env coerces START_PAGE env var string to int."""
    monkeypatch.setenv("START_PAGE", "3")
    params = ScraperParameters.from_env()
    assert params.start_page == 3


def test_from_env_max_page_negative_one_parsed_as_none() -> None:
    """Test from_env converts MAX_PAGE=-1 sentinel to None."""
    params = ScraperParameters.from_env()
    assert params.max_page is None


def test_from_env_max_page_positive_parsed_as_int(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test from_env coerces a positive MAX_PAGE env var string to int."""
    monkeypatch.setenv("MAX_PAGE", "5")
    params = ScraperParameters.from_env()
    assert params.max_page == 5


def test_max_long_retries_defaults_to_three(valid_scraper_env: dict) -> None:
    """Test max_long_retries defaults to 3 when not explicitly supplied."""
    params = ScraperParameters.model_validate(valid_scraper_env)
    assert params.max_long_retries == 3


def test_executed_at_is_auto_filled(valid_scraper_env: dict) -> None:
    """Test executed_at is auto-filled with a valid YYYY-MM-DDTHH:MM:SSZ timestamp."""
    params = ScraperParameters.model_validate(valid_scraper_env)
    datetime.strptime(params.executed_at, "%Y-%m-%dT%H:%M:%SZ")


def test_file_extension_defaults_to_json(valid_scraper_env: dict) -> None:
    """Test file_extension defaults to the JSON value."""
    params = ScraperParameters.model_validate(valid_scraper_env)
    assert params.file_extension == "json"


# ---------------------------------------------------------------------------
# BronzeParameters
# ---------------------------------------------------------------------------


def test_bronze_params_from_env_success(env: str, file_date: str, valid_bronze_env: dict) -> None:
    """Test BronzeParameters.from_env instantiates correctly from environment variables."""
    params = BronzeParameters.from_env()
    assert params.environment == env
    assert params.file_date == file_date
    assert params.upload_to_bq is (valid_bronze_env["upload_to_bq"].lower() == "true")


def test_bronze_params_from_env_raises_on_missing_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test BronzeParameters.from_env raises KeyError when a required env var is absent."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    with pytest.raises(KeyError):
        BronzeParameters.from_env()


def test_bronze_params_from_env_file_date_auto_fills_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test from_env auto-fills file_date with today's YYYY-MM-DD when FILE_DATE is absent."""
    monkeypatch.delenv("FILE_DATE", raising=False)
    params = BronzeParameters.from_env()
    datetime.strptime(params.file_date, "%Y-%m-%d")


def test_bronze_params_validate_file_date_accepts_valid_date(valid_bronze_env: dict) -> None:
    """Test validate_file_date accepts a well-formed YYYY-MM-DD string."""
    _date = "2026-06-15"
    params = BronzeParameters.model_validate({**valid_bronze_env, "file_date": _date})
    assert params.file_date == _date


def test_bronze_params_validate_file_date_raises_on_invalid_format(
    valid_bronze_env: dict,
) -> None:
    """Test validate_file_date raises ValidationError for a non-date string."""
    with pytest.raises(ValidationError, match="not a valid"):
        BronzeParameters.model_validate({**valid_bronze_env, "file_date": "not-a-date"})


def test_bronze_params_validate_file_date_raises_on_wrong_format(
    valid_bronze_env: dict,
) -> None:
    """Test validate_file_date raises ValidationError for a date in DD/MM/YYYY format."""
    with pytest.raises(ValidationError, match="not a valid"):
        BronzeParameters.model_validate({**valid_bronze_env, "file_date": "01/01/2026"})


def test_bronze_params_inherits_environment_validation(valid_bronze_env: dict) -> None:
    """Test BronzeParameters inherits the environment validator from InputParameters."""
    with pytest.raises(ValidationError, match="available environments"):
        BronzeParameters.model_validate({**valid_bronze_env, "environment": "staging"})


def test_bronze_params_inherits_city_validation(valid_bronze_env: dict) -> None:
    """Test BronzeParameters inherits the city validator from InputParameters."""
    with pytest.raises(ValidationError, match="available cities"):
        BronzeParameters.model_validate({**valid_bronze_env, "city": "rio"})


def test_bronze_params_inherits_sites_validation(valid_bronze_env: dict) -> None:
    """Test BronzeParameters inherits the sites validator from InputParameters."""
    with pytest.raises(ValidationError, match="not valid"):
        BronzeParameters.model_validate({**valid_bronze_env, "sites": "vivareal,unknown"})


def test_bronze_params_inherits_property_types_validation(valid_bronze_env: dict) -> None:
    """Test BronzeParameters inherits the property_types validator from InputParameters."""
    with pytest.raises(ValidationError, match="not valid"):
        BronzeParameters.model_validate({**valid_bronze_env, "property_types": "studio"})
