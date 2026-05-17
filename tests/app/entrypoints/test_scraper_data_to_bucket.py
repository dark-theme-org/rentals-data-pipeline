"""Test the scraper-to-GCS entrypoint pipeline."""

import json

import pytest
from pytest_mock import MockerFixture

import app.entrypoints.scraper_data_to_bucket as entry
from app.entrypoints.scraper_data_to_bucket import ScraperMapping, scraper_data_to_bucket
from app.utils.validations import ScraperParameters

_STORAGE_CLIENT = "app.entrypoints.scraper_data_to_bucket.storage.Client"
_GET_CREDENTIALS = "app.entrypoints.scraper_data_to_bucket.get_credentials"


def test_scraper_data_to_bucket_uploads_each_pair(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    item_list_payload: dict,
    scraper_params: ScraperParameters,
) -> None:
    """Test the entrypoint scrapes each (site, property_type) pair and uploads JSON to GCS."""
    monkeypatch.setattr(entry, "params", scraper_params)
    mocker.patch(_GET_CREDENTIALS)

    scraper_instance = mocker.MagicMock()
    scraper_instance.set_url.return_value = scraper_instance
    scraper_instance.fetch_and_parse_html.side_effect = [scraper_instance, None]
    scraper_instance.extract_properties.return_value = item_list_payload
    scraper_instance.get_site_name.return_value = "vivareal"
    scraper_class = mocker.MagicMock(return_value=scraper_instance)
    monkeypatch.setitem(entry.SCRAPER_MAPPING, "vivareal", ScraperMapping(scraper_class))

    blob = mocker.MagicMock()
    bucket = mocker.MagicMock()
    bucket.blob.return_value = blob
    client = mocker.MagicMock()
    client.bucket.return_value = bucket
    mocker.patch(_STORAGE_CLIENT, return_value=client)

    scraper_data_to_bucket()

    client.bucket.assert_called_once_with("scraper-rentals-data")
    blob.upload_from_string.assert_called_once()
    payload_arg, kwargs = blob.upload_from_string.call_args
    assert json.loads(payload_arg[0]) == item_list_payload
    assert kwargs["content_type"] == "application/json"


def test_scraper_data_to_bucket_skips_upload_when_flag_is_false(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    item_list_payload: dict,
    scraper_params_no_upload: ScraperParameters,
) -> None:
    """Test the entrypoint scrapes each pair but skips GCS upload when upload_to_gcs is False."""
    monkeypatch.setattr(entry, "params", scraper_params_no_upload)
    mocker.patch(_GET_CREDENTIALS)

    scraper_instance = mocker.MagicMock()
    scraper_instance.set_url.return_value = scraper_instance
    scraper_instance.fetch_and_parse_html.side_effect = [scraper_instance, None]
    scraper_instance.extract_properties.return_value = item_list_payload
    scraper_instance.get_site_name.return_value = "vivareal"
    scraper_class = mocker.MagicMock(return_value=scraper_instance)
    monkeypatch.setitem(entry.SCRAPER_MAPPING, "vivareal", ScraperMapping(scraper_class))

    blob = mocker.MagicMock()
    bucket = mocker.MagicMock()
    bucket.blob.return_value = blob
    client = mocker.MagicMock()
    client.bucket.return_value = bucket
    mocker.patch(_STORAGE_CLIENT, return_value=client)

    scraper_data_to_bucket()

    scraper_instance.extract_properties.assert_called_once()
    blob.upload_from_string.assert_not_called()


def test_scraper_data_to_bucket_stops_at_max_page(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    item_list_payload: dict,
    scraper_params_with_max_page: ScraperParameters,
) -> None:
    """Test the entrypoint stops fetching once max_page is reached."""
    monkeypatch.setattr(entry, "params", scraper_params_with_max_page)
    mocker.patch(_GET_CREDENTIALS)

    scraper_instance = mocker.MagicMock()
    scraper_instance.set_url.return_value = scraper_instance
    scraper_instance.fetch_and_parse_html.return_value = scraper_instance
    scraper_instance.extract_properties.return_value = item_list_payload
    scraper_instance.get_site_name.return_value = "vivareal"
    scraper_class = mocker.MagicMock(return_value=scraper_instance)
    monkeypatch.setitem(entry.SCRAPER_MAPPING, "vivareal", ScraperMapping(scraper_class))

    blob = mocker.MagicMock()
    bucket = mocker.MagicMock()
    bucket.blob.return_value = blob
    client = mocker.MagicMock()
    client.bucket.return_value = bucket
    mocker.patch(_STORAGE_CLIENT, return_value=client)

    scraper_data_to_bucket()

    assert scraper_instance.fetch_and_parse_html.call_count == 1
    blob.upload_from_string.assert_called_once()


def test_scraper_data_to_bucket_stops_on_404(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    scraper_params: ScraperParameters,
) -> None:
    """Test the entrypoint stops the page loop when fetch_and_parse_html returns None."""
    monkeypatch.setattr(entry, "params", scraper_params)
    mocker.patch(_GET_CREDENTIALS)

    scraper_instance = mocker.MagicMock()
    scraper_instance.set_url.return_value = scraper_instance
    scraper_instance.fetch_and_parse_html.return_value = None
    scraper_instance.get_site_name.return_value = "vivareal"
    scraper_class = mocker.MagicMock(return_value=scraper_instance)
    monkeypatch.setitem(entry.SCRAPER_MAPPING, "vivareal", ScraperMapping(scraper_class))

    blob = mocker.MagicMock()
    bucket = mocker.MagicMock()
    bucket.blob.return_value = blob
    client = mocker.MagicMock()
    client.bucket.return_value = bucket
    mocker.patch(_STORAGE_CLIENT, return_value=client)

    scraper_data_to_bucket()

    scraper_instance.fetch_and_parse_html.assert_called_once()
    scraper_instance.extract_properties.assert_not_called()
    blob.upload_from_string.assert_not_called()
