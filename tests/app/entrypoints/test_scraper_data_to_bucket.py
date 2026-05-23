"""Test the scraper-to-GCS entrypoint pipeline."""

import json
import os
from unittest.mock import MagicMock

import pytest
from curl_cffi.requests.exceptions import RequestException
from pytest_mock import MockerFixture

import app.entrypoints.scraper_data_to_bucket as entry
from app.data.scrapers.sites.viva_real import SITE_NAME_VIVA_REAL
from app.entrypoints.scraper_data_to_bucket import ScraperMapping, scraper_data_to_bucket
from app.utils.validations import ScraperParameters

_STORAGE_CLIENT = "app.entrypoints.scraper_data_to_bucket.storage.Client"
_GET_CREDENTIALS = "app.entrypoints.scraper_data_to_bucket.get_credentials"


def _single_scraper_params(env: str, expected_city: str, **overrides: object) -> ScraperParameters:
    return ScraperParameters.model_validate(
        {
            "environment": env,
            "city": expected_city,
            "sites": SITE_NAME_VIVA_REAL,
            "property_types": "apartment",
            "upload_to_gcs": True,
            "start_page": 1,
            "max_page": None,
            "version": os.environ.get("VERSION", "test"),
            **overrides,
        }
    )


@pytest.fixture(name="fast_long_sleep")
def fast_long_sleep_(mocker: MockerFixture) -> None:
    """No-op `time.sleep` so long-retry sleeps in the entrypoint don't actually wait."""
    mocker.patch("app.entrypoints.scraper_data_to_bucket.time.sleep")


@pytest.fixture(name="scraper_params")
def scraper_params_(env: str, expected_city: str) -> ScraperParameters:
    """ScraperParameters scoped to a single (site, property_type) pair for entrypoint tests."""
    return _single_scraper_params(env, expected_city)


@pytest.fixture(name="scraper_params_no_upload")
def scraper_params_no_upload_(env: str, expected_city: str) -> ScraperParameters:
    """ScraperParameters with upload_to_gcs=False for GCS-skip-path tests."""
    return _single_scraper_params(env, expected_city, upload_to_gcs=False)


@pytest.fixture(name="scraper_params_with_max_page")
def scraper_params_with_max_page_(env: str, expected_city: str) -> ScraperParameters:
    """ScraperParameters with max_page=1 for loop-termination tests."""
    return _single_scraper_params(env, expected_city, max_page=1)


@pytest.fixture(name="gcs_mocks")
def gcs_mocks_(mocker: MockerFixture) -> tuple:
    """Patch storage.Client and get_credentials; return (client, blob) for assertions."""
    mocker.patch(_GET_CREDENTIALS)
    blob = mocker.MagicMock()
    bucket = mocker.MagicMock()
    bucket.blob.return_value = blob
    client = mocker.MagicMock()
    client.bucket.return_value = bucket
    mocker.patch(_STORAGE_CLIENT, return_value=client)
    return client, blob


@pytest.fixture(name="scraper_mock")
def scraper_mock_(mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Stub scraper instance wired into SCRAPER_MAPPING; tests configure fetch/extract."""
    scraper_instance: MagicMock = mocker.MagicMock()
    scraper_instance.set_url.return_value = scraper_instance
    scraper_instance.get_site_name.return_value = SITE_NAME_VIVA_REAL
    scraper_class = mocker.MagicMock(return_value=scraper_instance)
    monkeypatch.setitem(entry.SCRAPER_MAPPING, SITE_NAME_VIVA_REAL, ScraperMapping(scraper_class))
    return scraper_instance


def test_scraper_data_to_bucket_uploads_each_pair(
    monkeypatch: pytest.MonkeyPatch,
    gcs_mocks: tuple,
    scraper_mock: MagicMock,
    item_list_payload: dict,
    scraper_params: ScraperParameters,
) -> None:
    """Test the entrypoint scrapes each (site, property_type) pair and uploads JSON to GCS."""
    monkeypatch.setattr(entry, "params", scraper_params)
    client, blob = gcs_mocks
    scraper_mock.fetch_and_parse_html.side_effect = [scraper_mock, None]
    scraper_mock.extract_properties.return_value = item_list_payload

    scraper_data_to_bucket()

    client.bucket.assert_called_once_with("scraper-rentals-data")
    blob.upload_from_string.assert_called_once()
    payload_arg, kwargs = blob.upload_from_string.call_args
    assert json.loads(payload_arg[0]) == item_list_payload
    assert kwargs["content_type"] == "application/json"


def test_scraper_data_to_bucket_skips_upload_when_flag_is_false(
    monkeypatch: pytest.MonkeyPatch,
    gcs_mocks: tuple,
    scraper_mock: MagicMock,
    item_list_payload: dict,
    scraper_params_no_upload: ScraperParameters,
) -> None:
    """Test the entrypoint scrapes each pair but skips GCS upload when upload_to_gcs is False."""
    monkeypatch.setattr(entry, "params", scraper_params_no_upload)
    _, blob = gcs_mocks
    scraper_mock.fetch_and_parse_html.side_effect = [scraper_mock, None]
    scraper_mock.extract_properties.return_value = item_list_payload

    scraper_data_to_bucket()

    scraper_mock.extract_properties.assert_called_once()
    blob.upload_from_string.assert_not_called()


def test_scraper_data_to_bucket_stops_at_max_page(
    monkeypatch: pytest.MonkeyPatch,
    gcs_mocks: tuple,
    scraper_mock: MagicMock,
    item_list_payload: dict,
    scraper_params_with_max_page: ScraperParameters,
) -> None:
    """Test the entrypoint stops fetching once max_page is reached."""
    monkeypatch.setattr(entry, "params", scraper_params_with_max_page)
    _, blob = gcs_mocks
    scraper_mock.fetch_and_parse_html.return_value = scraper_mock
    scraper_mock.extract_properties.return_value = item_list_payload

    scraper_data_to_bucket()

    assert scraper_mock.fetch_and_parse_html.call_count == 1
    blob.upload_from_string.assert_called_once()


def test_scraper_data_to_bucket_stops_on_404(
    monkeypatch: pytest.MonkeyPatch,
    gcs_mocks: tuple,
    scraper_mock: MagicMock,
    scraper_params: ScraperParameters,
) -> None:
    """Test the entrypoint stops the page loop when fetch_and_parse_html returns None."""
    monkeypatch.setattr(entry, "params", scraper_params)
    _, blob = gcs_mocks
    scraper_mock.fetch_and_parse_html.return_value = None

    scraper_data_to_bucket()

    scraper_mock.fetch_and_parse_html.assert_called_once()
    scraper_mock.extract_properties.assert_not_called()
    blob.upload_from_string.assert_not_called()


@pytest.mark.usefixtures("fast_long_sleep")
def test_scraper_data_to_bucket_long_retry_recovers_after_request_error(
    monkeypatch: pytest.MonkeyPatch,
    gcs_mocks: tuple,
    scraper_mock: MagicMock,
    item_list_payload: dict,
    scraper_params: ScraperParameters,
) -> None:
    """Test the entrypoint retries the same page after a RequestException then succeeds."""
    monkeypatch.setattr(entry, "params", scraper_params)
    _, blob = gcs_mocks
    scraper_mock.fetch_and_parse_html.side_effect = [
        RequestException("blocked"),
        scraper_mock,
        None,
    ]
    scraper_mock.extract_properties.return_value = item_list_payload

    scraper_data_to_bucket()

    assert scraper_mock.fetch_and_parse_html.call_count == 3
    blob.upload_from_string.assert_called_once()


@pytest.mark.usefixtures("fast_long_sleep")
def test_scraper_data_to_bucket_stops_after_max_long_retries(
    monkeypatch: pytest.MonkeyPatch,
    gcs_mocks: tuple,
    scraper_mock: MagicMock,
    scraper_params: ScraperParameters,
) -> None:
    """Test the entrypoint stops after exhausting all long retries on a persistent error."""
    monkeypatch.setattr(entry, "params", scraper_params)
    _, blob = gcs_mocks
    scraper_mock.fetch_and_parse_html.side_effect = RequestException("blocked")

    scraper_data_to_bucket()

    assert scraper_mock.fetch_and_parse_html.call_count == scraper_params.max_long_retries + 1
    blob.upload_from_string.assert_not_called()


def test_scraper_data_to_bucket_stops_on_empty_page(
    monkeypatch: pytest.MonkeyPatch,
    gcs_mocks: tuple,
    scraper_mock: MagicMock,
    scraper_params: ScraperParameters,
) -> None:
    """Test the entrypoint stops cleanly when extract_properties raises ValueError."""
    monkeypatch.setattr(entry, "params", scraper_params)
    _, blob = gcs_mocks
    scraper_mock.fetch_and_parse_html.return_value = scraper_mock
    scraper_mock.extract_properties.side_effect = ValueError("no ItemList")

    scraper_data_to_bucket()

    scraper_mock.extract_properties.assert_called_once()
    blob.upload_from_string.assert_not_called()
