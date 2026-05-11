"""Test enums and credential resolution exposed by the shared utils module."""

import pytest
from pytest_mock import MockerFixture

from app.utils.utils import Environment, FileExtensions, ServiceAccountNames, get_credentials


def test_environment_members() -> None:
    """Test Environment exposes DEV/TEST/PROD with lowercase string values."""
    assert Environment.DEV == "dev"
    assert Environment.TEST == "test"
    assert Environment.PROD == "prod"


def test_file_extensions_members() -> None:
    """Test FileExtensions exposes JSON with lowercase value."""
    assert FileExtensions.JSON == "json"


def test_get_credentials_returns_default_adc_when_env_unset(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test get_credentials returns the default ADC verbatim when the named env var is unset."""
    monkeypatch.delenv(ServiceAccountNames.GCS, raising=False)
    base_creds = mocker.Mock(name="base_creds")
    mocker.patch("app.utils.utils.google.auth.default", return_value=(base_creds, "some-project"))
    impersonated = mocker.patch("app.utils.utils.impersonated_credentials.Credentials")
    assert get_credentials(ServiceAccountNames.GCS) is base_creds
    impersonated.assert_not_called()


def test_get_credentials_impersonates_when_env_set(
    sa_email: str, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test get_credentials wraps default ADC in impersonated_credentials when env var is set."""
    monkeypatch.setenv(ServiceAccountNames.GCS, sa_email)
    base_creds = mocker.Mock(name="base_creds")
    mocker.patch("app.utils.utils.google.auth.default", return_value=(base_creds, "some-project"))
    impersonated = mocker.patch("app.utils.utils.impersonated_credentials.Credentials")
    assert get_credentials(ServiceAccountNames.GCS) is impersonated.return_value
    impersonated.assert_called_once_with(
        source_credentials=base_creds,
        target_principal=sa_email,
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
