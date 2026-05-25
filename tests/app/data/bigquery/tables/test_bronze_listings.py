"""Tests for the BronzeListingsTable BigQuery table descriptor."""

import pytest
from google.cloud import bigquery
from pytest_mock import MockerFixture

from app.data.bigquery import AuditMetadata, BronzeListingsTable
from app.data.gcs import ScraperBucket


@pytest.fixture(name="source_metadata")
def source_metadata_(
    scraper_bucket: ScraperBucket, file_date: str
) -> BronzeListingsTable.SourceMetadata:
    """SourceMetadata derived from the canonical scraper_bucket fixture."""
    ts = f"{file_date}T00:00:00Z"
    return BronzeListingsTable.SourceMetadata(
        blob=f"{scraper_bucket.prefix}/{ts}.json",
        site_name=scraper_bucket.site,
        city_name=scraper_bucket.city,
        property_type_cat=scraper_bucket.property_type,
        page_num=scraper_bucket.page,
        executed_at_ts=ts,
    )


def test_source_metadata_construction(
    source_metadata: BronzeListingsTable.SourceMetadata,
    scraper_bucket: ScraperBucket,
    file_date: str,
) -> None:
    """Test SourceMetadata stores all GCS lineage fields."""
    ts = f"{file_date}T00:00:00Z"
    assert source_metadata.blob == f"{scraper_bucket.prefix}/{ts}.json"
    assert source_metadata.site_name == scraper_bucket.site
    assert source_metadata.city_name == scraper_bucket.city
    assert source_metadata.property_type_cat == scraper_bucket.property_type
    assert source_metadata.page_num == scraper_bucket.page
    assert source_metadata.executed_at_ts == ts


def test_bronze_table_dataset(bronze_table: BronzeListingsTable, env: str) -> None:
    """Test dataset returns the environment name directly."""
    assert bronze_table.dataset == env


def test_bronze_table_table_name(bronze_table: BronzeListingsTable) -> None:
    """Test table returns the fixed bronze_listings name."""
    assert bronze_table.table == "bronze_listings"


def test_sql_file_paths_exist(bronze_table: BronzeListingsTable) -> None:
    """Test all three SQL file paths resolve to existing files on disk."""
    assert bronze_table.create_sql_file_path.exists()
    assert bronze_table.check_exists_sql_file_path.exists()
    assert bronze_table.check_table_exists_sql_file_path.exists()


def test_blob_already_loaded_returns_true(
    bronze_table: BronzeListingsTable,
    source_metadata: BronzeListingsTable.SourceMetadata,
    file_date: str,
    mocker: MockerFixture,
) -> None:
    """Test blob_already_loaded returns True when the check query finds a row."""
    client = mocker.MagicMock()
    client.query.return_value.result.return_value = iter([mocker.MagicMock()])
    assert (
        bronze_table.blob_already_loaded(
            client, blob_name=source_metadata.blob, executed_at=file_date
        )
        is True
    )


def test_blob_already_loaded_returns_false(
    bronze_table: BronzeListingsTable,
    source_metadata: BronzeListingsTable.SourceMetadata,
    file_date: str,
    mocker: MockerFixture,
) -> None:
    """Test blob_already_loaded returns False when the check query finds no rows."""
    client = mocker.MagicMock()
    client.query.return_value.result.return_value = iter([])
    assert (
        bronze_table.blob_already_loaded(
            client, blob_name=source_metadata.blob, executed_at=file_date
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

    assert row["LISTING_ID"] == raw_listing["@id"]
    assert row["LISTING_NAME"] == raw_listing["name"]
    assert row["LISTING_URL"] == raw_listing["url"]
    assert row["LISTING_DESCRIPTION"] == raw_listing["description"]
    assert row["LISTING_PETS_ALLOWED_FLAG"] is raw_listing["petsAllowed"]
    assert row["LISTING_NUMBER_OF_ROOMS_AMT"] == raw_listing["numberOfRooms"]
    assert row["LISTING_NUMBER_OF_BEDROOMS_AMT"] == raw_listing["numberOfBedrooms"]
    assert row["LISTING_NUMBER_OF_BATHROOMS_AMT"] == raw_listing["numberOfBathroomsTotal"]

    address = raw_listing["address"]
    assert row["LISTING_ADDRESS_INFOS"]["STREET_ADDRESS"] == address["streetAddress"]
    assert row["LISTING_ADDRESS_INFOS"]["LOCALITY"] == address["addressLocality"]
    assert row["LISTING_ADDRESS_INFOS"]["REGION"] == address["addressRegion"]
    assert row["LISTING_ADDRESS_INFOS"]["COUNTRY"] == address["addressCountry"]

    floor_size = raw_listing["floorSize"]
    assert row["LISTING_FLOOR_SIZE_INFOS"]["VALUE"] == floor_size["value"]
    assert row["LISTING_FLOOR_SIZE_INFOS"]["UNIT_CODE"] == floor_size["unitCode"]

    assert row["LISTING_IMAGES_LIST"] == raw_listing["image"]
    assert row["LISTING_AMENITY_FEATURES_INFOS"] == [
        {"NAME": f["name"], "VALUE": f["value"]} for f in raw_listing["amenityFeature"]
    ]

    offers = raw_listing["offers"]
    assert row["LISTING_OFFERS_INFOS"]["PRICE"] == offers["price"]
    assert row["LISTING_OFFERS_INFOS"]["PRICE_CURRENCY"] == offers["priceCurrency"]
    assert row["LISTING_OFFERS_INFOS"]["AVAILABILITY"] == offers["availability"]
    potential_action = offers["potentialAction"]
    assert row["LISTING_OFFERS_INFOS"]["POTENTIAL_ACTION"]["TARGET"] == potential_action["target"]
    price_spec = potential_action["priceSpecification"]
    assert (
        row["LISTING_OFFERS_INFOS"]["POTENTIAL_ACTION"]["PRICE_SPECIFICATION"]["PRICE"]
        == price_spec["price"]
    )
    prop_val = offers["propertyValue"]
    assert row["LISTING_OFFERS_INFOS"]["PROPERTY_VALUE"]["NAME"] == prop_val["name"]
    assert row["LISTING_OFFERS_INFOS"]["PROPERTY_VALUE"]["VALUE"] == prop_val["value"]
    assert row["LISTING_OFFERS_INFOS"]["PROPERTY_VALUE"]["UNIT_TEXT"] == prop_val["unitText"]

    assert row["SRC_BLOB"] == source_metadata.blob
    assert row["SRC_SITE_NAME"] == source_metadata.site_name
    assert row["SRC_CITY_NAME"] == source_metadata.city_name
    assert row["SRC_PROPERTY_TYPE_CAT"] == source_metadata.property_type_cat
    assert row["SRC_PAGE_NUM"] == source_metadata.page_num
    assert row["SRC_EXECUTED_AT_TS"] == source_metadata.executed_at_ts

    assert row["AUD_VERSION_ID"] == audit_metadata.version_id
    assert row["AUD_INS_TS"] == audit_metadata.ins_ts
    assert row["AUD_UPD_TS"] == audit_metadata.upd_ts


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
    assert row["LISTING_AMENITY_FEATURES_INFOS"] == []
