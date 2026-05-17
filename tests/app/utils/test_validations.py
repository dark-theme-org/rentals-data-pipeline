"""Tests for ScraperParameters input validation."""

import pytest
from pydantic import ValidationError

from app.utils.validations import ScraperParameters


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


def test_executed_at_is_auto_filled(valid_scraper_env: dict) -> None:
    """Test executed_at is populated automatically when not supplied."""
    params = ScraperParameters.model_validate(valid_scraper_env)
    assert params.executed_at


def test_file_extension_defaults_to_json(valid_scraper_env: dict) -> None:
    """Test file_extension defaults to the JSON value."""
    params = ScraperParameters.model_validate(valid_scraper_env)
    assert params.file_extension == "json"
