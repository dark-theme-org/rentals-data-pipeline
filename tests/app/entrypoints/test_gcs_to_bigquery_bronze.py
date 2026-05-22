"""Tests for the gcs_to_bigquery_bronze entrypoint."""

import json

import pytest
from pytest_mock import MockerFixture

import app.entrypoints.gcs_to_bigquery_bronze as entry
from app.entrypoints.gcs_to_bigquery_bronze import gcs_to_bigquery_bronze
from app.utils.validations import BronzeParameters

_BQ_CLIENT = "app.entrypoints.gcs_to_bigquery_bronze.bigquery.Client"
_STORAGE_CLIENT = "app.entrypoints.gcs_to_bigquery_bronze.storage.Client"
_GET_CREDENTIALS = "app.entrypoints.gcs_to_bigquery_bronze.get_credentials"


def test_creates_table_and_loads_rows_on_success_path(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    raw_listing: dict,
) -> None:
    """Test the entrypoint creates the table when absent and loads rows for one blob."""
    single_pair = BronzeParameters.model_validate(
        {
            "environment": "dev",
            "city": "macae",
            "sites": "vivareal",
            "property_types": "apartment",
            "upload_to_bq": True,
            "file_date": "2026-01-01",
            "version": "test",
            "start_page": 1,
            "max_page": None,
        }
    )
    monkeypatch.setattr(entry, "params", single_pair)
    mocker.patch(_GET_CREDENTIALS)

    mock_row = mocker.MagicMock()
    mock_row.CNT = 0
    bq_client = mocker.MagicMock()
    bq_client.query.return_value.result.return_value = iter([mock_row])

    blob = mocker.MagicMock()
    blob.name = "dev/vivareal/macae/apartment/1/2026-01-01T00:00:00Z.json"
    blob.updated = None
    blob.download_as_text.return_value = json.dumps({"id1": raw_listing})

    gcs_client = mocker.MagicMock()
    gcs_client.list_blobs.side_effect = [
        iter([blob]),
        iter([]),
    ]

    mocker.patch(_BQ_CLIENT, return_value=bq_client)
    mocker.patch(_STORAGE_CLIENT, return_value=gcs_client)

    gcs_to_bigquery_bronze()

    bq_client.load_table_from_json.assert_called_once()


def test_skips_upload_when_upload_to_bq_false(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test the entrypoint skips load_table_from_json when UPLOAD_TO_BQ=false."""
    no_upload = BronzeParameters.model_validate(
        {
            "environment": "dev",
            "city": "macae",
            "sites": "vivareal",
            "property_types": "apartment",
            "upload_to_bq": False,
            "file_date": "2026-01-01",
            "version": "test",
            "start_page": 1,
            "max_page": None,
        }
    )
    monkeypatch.setattr(entry, "params", no_upload)
    mocker.patch(_GET_CREDENTIALS)

    mock_row = mocker.MagicMock()
    mock_row.CNT = 1
    bq_client = mocker.MagicMock()
    bq_client.query.return_value.result.return_value = iter([mock_row])

    blob = mocker.MagicMock()
    blob.name = "dev/vivareal/macae/apartment/1/2026-01-01T00:00:00Z.json"
    blob.updated = None
    blob.download_as_text.return_value = "{}"

    gcs_client = mocker.MagicMock()
    gcs_client.list_blobs.side_effect = [iter([blob]), iter([])]

    mocker.patch(_BQ_CLIENT, return_value=bq_client)
    mocker.patch(_STORAGE_CLIENT, return_value=gcs_client)

    gcs_to_bigquery_bronze()

    bq_client.load_table_from_json.assert_not_called()


def test_stops_pagination_when_no_blob_found(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    bronze_params: BronzeParameters,
) -> None:
    """Test the while loop breaks when latest_blob returns None for a page."""
    monkeypatch.setattr(entry, "params", bronze_params)
    mocker.patch(_GET_CREDENTIALS)

    mock_row = mocker.MagicMock()
    mock_row.CNT = 1
    bq_client = mocker.MagicMock()
    bq_client.query.return_value.result.return_value = iter([mock_row])

    gcs_client = mocker.MagicMock()
    gcs_client.list_blobs.return_value = iter([])

    mocker.patch(_BQ_CLIENT, return_value=bq_client)
    mocker.patch(_STORAGE_CLIENT, return_value=gcs_client)

    gcs_to_bigquery_bronze()

    bq_client.load_table_from_json.assert_not_called()
