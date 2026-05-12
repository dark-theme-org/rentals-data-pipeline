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

    client.bucket.assert_called_once_with("scraper-rentals-data")
    blob.upload_from_string.assert_called_once()
    payload_arg, kwargs = blob.upload_from_string.call_args
    assert json.loads(payload_arg[0]) == item_list_payload
    assert kwargs["content_type"] == "application/json"
