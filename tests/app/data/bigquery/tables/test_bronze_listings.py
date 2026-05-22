"""Tests for the BronzeListingsTable BigQuery table descriptor."""

from google.cloud import bigquery
from pytest_mock import MockerFixture

from app.data.bigquery import AuditMetadata, BronzeListingsTable


def test_source_metadata_construction(
    source_metadata: BronzeListingsTable.SourceMetadata,
) -> None:
    """Test SourceMetadata stores all GCS lineage fields."""
    assert source_metadata.blob == "dev/vivareal/macae/apartment/1/2026-01-01T00:00:00Z.json"
    assert source_metadata.site_name == "vivareal"
    assert source_metadata.page_num == 1
    assert source_metadata.executed_at_ts == "2026-01-01T00:00:00Z"


def test_bronze_table_dataset(bronze_table: BronzeListingsTable) -> None:
    """Test dataset returns env-scoped name."""
    assert bronze_table.dataset == "dev_bronze"


def test_bronze_table_table_name(bronze_table: BronzeListingsTable) -> None:
    """Test table returns the fixed listings name."""
    assert bronze_table.table == "listings"


def test_sql_file_paths_exist(bronze_table: BronzeListingsTable) -> None:
    """Test all three SQL file paths resolve to existing files on disk."""
    assert bronze_table.create_sql_file_path.exists()
    assert bronze_table.check_exists_sql_file_path.exists()
    assert bronze_table.check_table_exists_sql_file_path.exists()


def test_blob_already_loaded_returns_true(
    bronze_table: BronzeListingsTable,
    mocker: MockerFixture,
) -> None:
    """Test blob_already_loaded returns True when the check query finds a row."""
    client = mocker.MagicMock()
    client.query.return_value.result.return_value = iter([mocker.MagicMock()])
    assert (
        bronze_table.blob_already_loaded(
            client,
            blob_name="dev/vivareal/macae/apartment/1/blob.json",
            executed_at="2026-01-01",
        )
        is True
    )


def test_blob_already_loaded_returns_false(
    bronze_table: BronzeListingsTable,
    mocker: MockerFixture,
) -> None:
    """Test blob_already_loaded returns False when the check query finds no rows."""
    client = mocker.MagicMock()
    client.query.return_value.result.return_value = iter([])
    assert (
        bronze_table.blob_already_loaded(
            client,
            blob_name="dev/vivareal/macae/apartment/1/blob.json",
            executed_at="2026-01-01",
        )
        is False
    )


def test_load_job_config_is_write_append(bronze_table: BronzeListingsTable) -> None:
    """Test load_job_config uses WRITE_APPEND write disposition."""
    assert bronze_table.load_job_config.write_disposition == bigquery.WriteDisposition.WRITE_APPEND


def test_row_schema_maps_listing_fields(
    bronze_table: BronzeListingsTable,
    source_metadata: BronzeListingsTable.SourceMetadata,
    audit_metadata: AuditMetadata,
    raw_listing: dict,
) -> None:
    """Test row_schema produces a dict with all expected column keys and values."""
    row = bronze_table.row_schema(raw_listing, src=source_metadata, aud=audit_metadata)

    assert row["LISTING_ID"] == "12345"
    assert row["LISTING_NAME"] == "Test Apartment"
    assert row["LISTING_PETS_ALLOWED_FLAG"] is False
    assert row["LISTING_NUMBER_OF_BEDROOMS_AMT"] == 2
    assert row["LISTING_ADDRESS_INFOS"]["LOCALITY"] == "Macaé"
    assert row["LISTING_FLOOR_SIZE_INFOS"]["VALUE"] == 60
    assert row["LISTING_IMAGES_LIST"] == ["https://example.com/img1.jpg"]
    assert row["LISTING_AMENITY_FEATURES_INFOS"] == [{"NAME": "Amenity", "VALUE": "Pool"}]
    assert row["LISTING_OFFERS_INFOS"]["PRICE"] == 2000
    assert row["SRC_BLOB"] == source_metadata.blob
    assert row["SRC_SITE_NAME"] == "vivareal"
    assert row["SRC_PAGE_NUM"] == 1
    assert row["AUD_VERSION_ID"] == "test"


def test_row_schema_handles_missing_nested_fields(
    bronze_table: BronzeListingsTable,
    source_metadata: BronzeListingsTable.SourceMetadata,
    audit_metadata: AuditMetadata,
) -> None:
    """Test row_schema returns None for absent nested fields rather than raising."""
    minimal_listing = {"@id": "999", "name": "Minimal"}
    row = bronze_table.row_schema(minimal_listing, src=source_metadata, aud=audit_metadata)
    assert row["LISTING_ADDRESS_INFOS"] is None
    assert row["LISTING_FLOOR_SIZE_INFOS"] is None
    assert row["LISTING_OFFERS_INFOS"] is None
    assert row["LISTING_IMAGES_LIST"] == []
