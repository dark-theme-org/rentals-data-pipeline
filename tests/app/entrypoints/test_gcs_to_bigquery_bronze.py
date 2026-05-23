"""Tests for the gcs_to_bigquery_bronze entrypoint."""

import json
import os

import pytest
from pytest_mock import MockerFixture

import app.entrypoints.gcs_to_bigquery_bronze as entry
from app.data.scrapers.sites.viva_real import SITE_NAME_VIVA_REAL
from app.entrypoints.gcs_to_bigquery_bronze import gcs_to_bigquery_bronze
from app.utils.validations import BronzeParameters

_BQ_CLIENT = "app.entrypoints.gcs_to_bigquery_bronze.bigquery.Client"
_STORAGE_CLIENT = "app.entrypoints.gcs_to_bigquery_bronze.storage.Client"
_GET_CREDENTIALS = "app.entrypoints.gcs_to_bigquery_bronze.get_credentials"

_BLOB_NAME = f"dev/{SITE_NAME_VIVA_REAL}/macae/apartment/1/{os.environ['FILE_DATE']}T00:00:00Z.json"


def _single_pair_params(env: str, expected_city: str, **overrides: object) -> BronzeParameters:
    return BronzeParameters.model_validate(
        {
            "environment": env,
            "city": expected_city,
            "sites": SITE_NAME_VIVA_REAL,
            "property_types": "apartment",
            "upload_to_bq": True,
            "file_date": os.environ["FILE_DATE"],
            "version": os.environ.get("VERSION", "test"),
            "start_page": 1,
            "max_page": None,
            **overrides,
        }
    )


@pytest.fixture(name="bronze_params")
def bronze_params_(env: str, expected_city: str) -> BronzeParameters:
    """BronzeParameters covering all sites and property types for pagination tests."""
    return BronzeParameters.model_validate(
        {
            "environment": env,
            "city": expected_city,
            "sites": os.environ["SITES"],
            "property_types": os.environ["PROPERTY_TYPES"],
            "upload_to_bq": os.environ["UPLOAD_TO_BQ"],
            "file_date": os.environ["FILE_DATE"],
            "version": os.environ.get("VERSION", "test"),
            "start_page": int(os.environ["START_PAGE"]),
            "max_page": None,
        }
    )


@pytest.fixture(name="bronze_params_single_pair")
def bronze_params_single_pair_(env: str, expected_city: str) -> BronzeParameters:
    """BronzeParameters scoped to a single (vivareal, apartment) pair for entrypoint tests."""
    return _single_pair_params(env, expected_city)


@pytest.fixture(name="bronze_params_single_pair_no_upload")
def bronze_params_single_pair_no_upload_(env: str, expected_city: str) -> BronzeParameters:
    """BronzeParameters with upload_to_bq=False for BQ-skip-path tests."""
    return _single_pair_params(env, expected_city, upload_to_bq=False)


@pytest.fixture(name="bronze_params_with_max_page")
def bronze_params_with_max_page_(env: str, expected_city: str) -> BronzeParameters:
    """BronzeParameters with max_page=1 for loop-termination tests."""
    return _single_pair_params(env, expected_city, max_page=1)


def test_creates_table_and_loads_rows_on_success_path(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    raw_listing: dict,
    bronze_params_single_pair: BronzeParameters,
) -> None:
    """Test the entrypoint creates the table when absent and loads rows for one blob."""
    monkeypatch.setattr(entry, "params", bronze_params_single_pair)
    mocker.patch(_GET_CREDENTIALS)

    mock_row = mocker.MagicMock()
    mock_row.CNT = 0
    bq_client = mocker.MagicMock()
    bq_client.query.return_value.result.return_value = iter([mock_row])

    blob = mocker.MagicMock()
    blob.name = _BLOB_NAME
    blob.updated = None
    blob.download_as_text.return_value = json.dumps({"id1": raw_listing})

    gcs_client = mocker.MagicMock()
    gcs_client.list_blobs.side_effect = [iter([blob]), iter([])]

    mocker.patch(_BQ_CLIENT, return_value=bq_client)
    mocker.patch(_STORAGE_CLIENT, return_value=gcs_client)

    gcs_to_bigquery_bronze()

    bq_client.load_table_from_json.assert_called_once()


def test_table_already_exists_does_not_call_create(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    bronze_params_single_pair: BronzeParameters,
) -> None:
    """Test the entrypoint skips table.create when the table already exists."""
    monkeypatch.setattr(entry, "params", bronze_params_single_pair)
    mocker.patch(_GET_CREDENTIALS)

    bq_client = mocker.MagicMock()
    bq_client.query.return_value.result.return_value = iter([mocker.MagicMock(CNT=1)])

    gcs_client = mocker.MagicMock()
    gcs_client.list_blobs.return_value = iter([])

    mocker.patch(_BQ_CLIENT, return_value=bq_client)
    mocker.patch(_STORAGE_CLIENT, return_value=gcs_client)

    gcs_to_bigquery_bronze()

    bq_client.query.assert_called_once()  # only the exists check, no create DDL
    bq_client.load_table_from_json.assert_not_called()


def test_skips_blob_already_loaded(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    bronze_params_single_pair: BronzeParameters,
) -> None:
    """Test the entrypoint skips a blob that was already loaded and moves to the next page."""
    monkeypatch.setattr(entry, "params", bronze_params_single_pair)
    mocker.patch(_GET_CREDENTIALS)

    bq_client = mocker.MagicMock()
    bq_client.query.return_value.result.side_effect = [
        iter([mocker.MagicMock(CNT=1)]),  # exists → True, skip create
        iter([mocker.MagicMock()]),  # blob_already_loaded → True (non-empty row)
    ]

    blob = mocker.MagicMock()
    blob.name = _BLOB_NAME
    blob.updated = None

    gcs_client = mocker.MagicMock()
    gcs_client.list_blobs.side_effect = [iter([blob]), iter([])]

    mocker.patch(_BQ_CLIENT, return_value=bq_client)
    mocker.patch(_STORAGE_CLIENT, return_value=gcs_client)

    gcs_to_bigquery_bronze()

    blob.download_as_text.assert_not_called()
    bq_client.load_table_from_json.assert_not_called()


def test_skips_upload_when_upload_to_bq_false(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    bronze_params_single_pair_no_upload: BronzeParameters,
) -> None:
    """Test the entrypoint skips load_table_from_json when upload_to_bq is False."""
    monkeypatch.setattr(entry, "params", bronze_params_single_pair_no_upload)
    mocker.patch(_GET_CREDENTIALS)

    mock_row = mocker.MagicMock()
    mock_row.CNT = 1
    bq_client = mocker.MagicMock()
    bq_client.query.return_value.result.return_value = iter([mock_row])

    blob = mocker.MagicMock()
    blob.name = _BLOB_NAME
    blob.updated = None
    blob.download_as_text.return_value = json.dumps({})

    gcs_client = mocker.MagicMock()
    gcs_client.list_blobs.side_effect = [iter([blob]), iter([])]

    mocker.patch(_BQ_CLIENT, return_value=bq_client)
    mocker.patch(_STORAGE_CLIENT, return_value=gcs_client)

    gcs_to_bigquery_bronze()

    blob.download_as_text.assert_called_once()
    bq_client.load_table_from_json.assert_not_called()


def test_stops_at_max_page(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    raw_listing: dict,
    bronze_params_with_max_page: BronzeParameters,
) -> None:
    """Test the entrypoint stops fetching blobs once max_page is reached."""
    monkeypatch.setattr(entry, "params", bronze_params_with_max_page)
    mocker.patch(_GET_CREDENTIALS)

    bq_client = mocker.MagicMock()
    bq_client.query.return_value.result.side_effect = [
        iter([mocker.MagicMock(CNT=1)]),  # exists → True
        iter([]),  # blob_already_loaded → False (empty → None)
    ]

    blob = mocker.MagicMock()
    blob.name = _BLOB_NAME
    blob.updated = None
    blob.download_as_text.return_value = json.dumps({"id1": raw_listing})

    gcs_client = mocker.MagicMock()
    gcs_client.list_blobs.return_value = iter([blob])

    mocker.patch(_BQ_CLIENT, return_value=bq_client)
    mocker.patch(_STORAGE_CLIENT, return_value=gcs_client)

    gcs_to_bigquery_bronze()

    assert gcs_client.list_blobs.call_count == 1
    bq_client.load_table_from_json.assert_called_once()


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
