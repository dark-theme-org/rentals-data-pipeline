"""Test enums and credential resolution exposed by the shared utils module."""

from datetime import datetime

import pytest
from pytest_mock import MockerFixture

from app.utils.utils import (
    CloudSettings,
    Environment,
    FileExtensions,
    ServiceAccountNames,
    datetime_now_utc,
    get_credentials,
)


@pytest.fixture(name="sa_email")
def sa_email_() -> str:
    """Throwaway service-account email used by credential-resolution tests."""
    return "test-sa@example.iam.gserviceaccount.com"


def test_environment_members() -> None:
    """Test Environment exposes DEV/TEST/PROD with lowercase string values."""
    assert Environment.DEV == "dev"
    assert Environment.TEST == "test"
    assert Environment.PROD == "prod"


def test_file_extensions_members() -> None:
    """Test FileExtensions exposes JSON with lowercase value."""
    assert FileExtensions.JSON == "json"


def test_service_account_names_members() -> None:
    """Test ServiceAccountNames exposes the expected env-var name strings."""
    assert ServiceAccountNames.BQ == "BQ_SA"
    assert ServiceAccountNames.GCS == "GCS_SA"


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


@pytest.fixture(name="gcp_auth_mocks")
def gcp_auth_mocks_(mocker: MockerFixture) -> tuple:
    """Patch google.auth.default and impersonated_credentials, return (base_creds, impersonated)."""
    base_creds = mocker.Mock(name="base_creds")
    mocker.patch(
        "app.utils.utils.google.auth.default",
        return_value=(base_creds, CloudSettings.PROJECT_ID),
    )
    impersonated = mocker.patch("app.utils.utils.impersonated_credentials.Credentials")
    return base_creds, impersonated


def test_get_credentials_returns_default_adc_when_env_unset(
    gcp_auth_mocks: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test get_credentials returns the default ADC verbatim when the named env var is unset."""
    base_creds, impersonated = gcp_auth_mocks
    monkeypatch.delenv(ServiceAccountNames.GCS, raising=False)
    assert get_credentials(ServiceAccountNames.GCS) is base_creds
    impersonated.assert_not_called()


def test_get_credentials_impersonates_when_env_set(
    sa_email: str, gcp_auth_mocks: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test get_credentials wraps default ADC in impersonated_credentials when env var is set."""
    base_creds, impersonated = gcp_auth_mocks
    monkeypatch.setenv(ServiceAccountNames.GCS, sa_email)
    assert get_credentials(ServiceAccountNames.GCS) is impersonated.return_value
    impersonated.assert_called_once_with(
        source_credentials=base_creds,
        target_principal=sa_email,
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
