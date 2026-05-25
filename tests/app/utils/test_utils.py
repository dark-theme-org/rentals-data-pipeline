"""Test enums and credential resolution exposed by the shared utils module."""

from datetime import datetime

from pytest_mock import MockerFixture

from app.utils.utils import (
    CloudSettings,
    Environment,
    FileExtensions,
    datetime_now_utc,
    get_credentials,
)


def test_environment_members() -> None:
    """Test Environment exposes DEV/TEST/PROD with lowercase string values."""
    assert Environment.DEV == "dev"
    assert Environment.TEST == "test"
    assert Environment.PROD == "prod"


def test_file_extensions_members() -> None:
    """Test FileExtensions exposes JSON with lowercase value."""
    assert FileExtensions.JSON == "json"


def test_cloud_settings_members_are_non_empty_strings() -> None:
    """Test CloudSettings loads non-empty PROJECT_ID and REGION from cloud/settings.yml."""
    assert CloudSettings.PROJECT_ID
    assert CloudSettings.REGION


def test_datetime_now_utc_returns_full_iso_format() -> None:
    """Test datetime_now_utc returns a valid YYYY-MM-DDTHH:MM:SSZ string by default."""
    datetime.strptime(datetime_now_utc(), "%Y-%m-%dT%H:%M:%SZ")


def test_datetime_now_utc_with_date_trunc_returns_date_only() -> None:
    """Test datetime_now_utc returns a valid YYYY-MM-DD string when date_trunc=True."""
    datetime.strptime(datetime_now_utc(date_trunc=True), "%Y-%m-%d")


def test_get_credentials_returns_adc(mocker: MockerFixture) -> None:
    """Test get_credentials returns the ADC credentials directly."""
    base_creds = mocker.Mock(name="base_creds")
    mocker.patch(
        "app.utils.utils.google.auth.default",
        return_value=(base_creds, CloudSettings.PROJECT_ID),
    )
    assert get_credentials() is base_creds
