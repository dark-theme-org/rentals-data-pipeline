"""Tests for ScraperParameters and BronzeParameters input validation."""

import pytest
from pydantic import ValidationError

from app.utils.validations import BronzeParameters, ScraperParameters


def test_from_env_success(monkeypatch: pytest.MonkeyPatch, valid_scraper_env: dict) -> None:
    """Test from_env returns a valid ScraperParameters from environment variables."""
    for key, value in valid_scraper_env.items():
        monkeypatch.setenv(key.upper(), value)
    params = ScraperParameters.from_env()
    assert params.environment == "dev"
    assert params.city == "macae"
    assert params.sites == ["vivareal", "zapimoveis"]
    assert params.property_types == ["apartment", "house"]
    assert params.upload_to_gcs is True
    assert params.start_page == 1
    assert params.max_page is None


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
    monkeypatch: pytest.MonkeyPatch, valid_scraper_env: dict
) -> None:
    """Test from_env coerces UPLOAD_TO_GCS="false" to bool False via Pydantic lax validation."""
    for key, value in valid_scraper_env.items():
        monkeypatch.setenv(key.upper(), value)
    monkeypatch.setenv("UPLOAD_TO_GCS", "false")
    params = ScraperParameters.from_env()
    assert params.upload_to_gcs is False


def test_from_env_upload_to_gcs_capital_true_parsed_as_bool(
    monkeypatch: pytest.MonkeyPatch, valid_scraper_env: dict
) -> None:
    """Test from_env coerces UPLOAD_TO_GCS="True" (str(True) from setup_docker.py) to bool True."""
    for key, value in valid_scraper_env.items():
        monkeypatch.setenv(key.upper(), value)
    monkeypatch.setenv("UPLOAD_TO_GCS", "True")
    params = ScraperParameters.from_env()
    assert params.upload_to_gcs is True


def test_from_env_start_page_parsed_as_int(
    monkeypatch: pytest.MonkeyPatch, valid_scraper_env: dict
) -> None:
    """Test from_env coerces START_PAGE env var string to int."""
    for key, value in valid_scraper_env.items():
        monkeypatch.setenv(key.upper(), value)
    monkeypatch.setenv("START_PAGE", "3")
    params = ScraperParameters.from_env()
    assert params.start_page == 3


def test_from_env_max_page_negative_one_parsed_as_none(
    monkeypatch: pytest.MonkeyPatch, valid_scraper_env: dict
) -> None:
    """Test from_env converts MAX_PAGE=-1 sentinel to None."""
    for key, value in valid_scraper_env.items():
        monkeypatch.setenv(key.upper(), value)
    params = ScraperParameters.from_env()
    assert params.max_page is None


def test_from_env_max_page_positive_parsed_as_int(
    monkeypatch: pytest.MonkeyPatch, valid_scraper_env: dict
) -> None:
    """Test from_env coerces a positive MAX_PAGE env var string to int."""
    for key, value in valid_scraper_env.items():
        monkeypatch.setenv(key.upper(), value)
    monkeypatch.setenv("MAX_PAGE", "5")
    params = ScraperParameters.from_env()
    assert params.max_page == 5


def test_max_long_retries_defaults_to_three(valid_scraper_env: dict) -> None:
    """Test max_long_retries defaults to 3 when not explicitly supplied."""
    params = ScraperParameters.model_validate(valid_scraper_env)
    assert params.max_long_retries == 3


def test_executed_at_is_auto_filled(valid_scraper_env: dict) -> None:
    """Test executed_at is populated automatically when not supplied."""
    params = ScraperParameters.model_validate(valid_scraper_env)
    assert params.executed_at


def test_file_extension_defaults_to_json(valid_scraper_env: dict) -> None:
    """Test file_extension defaults to the JSON value."""
    params = ScraperParameters.model_validate(valid_scraper_env)
    assert params.file_extension == "json"


# ---------------------------------------------------------------------------
# BronzeParameters
# ---------------------------------------------------------------------------


def test_bronze_params_from_env_success(
    monkeypatch: pytest.MonkeyPatch, valid_bronze_env: dict
) -> None:
    """Test BronzeParameters.from_env instantiates correctly from environment variables."""
    monkeypatch.setenv("ENVIRONMENT", valid_bronze_env["environment"])
    monkeypatch.setenv("CITY", valid_bronze_env["city"])
    monkeypatch.setenv("SITES", valid_bronze_env["sites"])
    monkeypatch.setenv("PROPERTY_TYPES", valid_bronze_env["property_types"])
    monkeypatch.setenv("UPLOAD_TO_BQ", str(valid_bronze_env["upload_to_bq"]).lower())
    monkeypatch.setenv("FILE_DATE", valid_bronze_env["file_date"])
    monkeypatch.setenv("START_PAGE", str(valid_bronze_env["start_page"]))
    monkeypatch.setenv("MAX_PAGE", "-1")
    params = BronzeParameters.from_env()
    assert params.environment == "dev"
    assert params.file_date == "2026-01-01"
    assert params.upload_to_bq is True


def test_bronze_params_validate_file_date_accepts_valid_date(
    valid_bronze_env: dict,
) -> None:
    """Test validate_file_date accepts a well-formed YYYY-MM-DD string."""
    params = BronzeParameters.model_validate({**valid_bronze_env, "file_date": "2026-06-15"})
    assert params.file_date == "2026-06-15"


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
