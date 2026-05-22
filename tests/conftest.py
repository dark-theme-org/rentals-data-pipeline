"""Project-wide pytest fixtures shared across the test suite."""

import json
import os

import pytest
from pytest_mock import MockerFixture

from app.data.bigquery import AuditMetadata, BronzeListingsTable
from app.data.gcs import ScraperBucket
from app.utils import Environment, FileExtensions
from app.utils.validations import BronzeParameters, ScraperParameters


@pytest.fixture(name="env")
def env_() -> Environment:
    """Deployment environment read from the ENVIRONMENT pytest.ini variable."""
    return Environment(os.environ["ENVIRONMENT"])


@pytest.fixture(name="file_extension")
def file_extension_() -> FileExtensions:
    """Default file extension for blob payloads."""
    return FileExtensions.JSON


@pytest.fixture(name="scraper_bucket")
def scraper_bucket_(env: Environment, expected_city: str) -> ScraperBucket:
    """ScraperBucket bound to a canonical (env, site, city, property_type, page) tuple."""
    return ScraperBucket(
        env=env, site="vivareal", city=expected_city, property_type="apartment", page=1
    )


@pytest.fixture(name="expected_city")
def expected_city_() -> str:
    """City slug read from the CITY pytest.ini variable."""
    return os.environ["CITY"]


@pytest.fixture(name="expected_uf")
def expected_uf_() -> str:
    """Canonical two-letter UF code expected for `UF.RJ`."""
    return "rj"


@pytest.fixture(name="sa_email")
def sa_email_() -> str:
    """Throwaway service-account email used by credential-resolution tests."""
    return "test-sa@example.iam.gserviceaccount.com"


@pytest.fixture(name="property_apartment")
def property_apartment_() -> str:
    """Stand-in slug used to construct the `apartment` field on `PropertyTypes`."""
    return "ap"


@pytest.fixture(name="property_house")
def property_house_() -> str:
    """Stand-in slug used to construct the `house` field on `PropertyTypes`."""
    return "ho"


@pytest.fixture(name="item_list_payload")
def item_list_payload_() -> dict:
    """JSON-LD ItemList payload with two listings."""
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "item": {
                    "@id": "https://example.com/listing/1",
                    "@type": "Apartment",
                    "name": "Listing 1",
                },
            },
            {
                "@type": "ListItem",
                "position": 2,
                "item": {
                    "@id": "https://example.com/listing/2",
                    "@type": "Apartment",
                    "name": "Listing 2",
                },
            },
        ],
    }


@pytest.fixture(name="html_with_item_list")
def html_with_item_list_(item_list_payload: dict) -> str:
    """HTML page containing an `ItemList` JSON-LD block alongside an unrelated block."""
    return f"""
    <html>
      <head>
        <script type="application/ld+json">
          {{"@context": "https://schema.org", "@type": "WebPage", "name": "Sample"}}
        </script>
        <script type="application/ld+json">
          {json.dumps(item_list_payload)}
        </script>
      </head>
      <body><p>Listings</p></body>
    </html>
    """


@pytest.fixture(name="html_without_item_list")
def html_without_item_list_() -> str:
    """HTML page with JSON-LD blocks but no `ItemList`."""
    return """
    <html>
      <head>
        <script type="application/ld+json">
          {"@context": "https://schema.org", "@type": "WebPage", "name": "Sample"}
        </script>
      </head>
      <body><p>No listings</p></body>
    </html>
    """


@pytest.fixture(name="html_with_bad_json")
def html_with_bad_json_() -> str:
    """HTML page with a malformed JSON-LD block."""
    return """
    <html>
      <head>
        <script type="application/ld+json">{not valid json}</script>
      </head>
    </html>
    """


@pytest.fixture(name="fast_retry")
def fast_retry_(mocker: MockerFixture) -> None:
    """No-op `tenacity` sleep so retry-decorated calls don't actually wait."""
    mocker.patch("tenacity.nap.time.sleep")


@pytest.fixture(name="fast_long_sleep")
def fast_long_sleep_(mocker: MockerFixture) -> None:
    """No-op `time.sleep` so long-retry sleeps in the entrypoint don't actually wait."""
    mocker.patch("app.entrypoints.scraper_data_to_bucket.time.sleep")


@pytest.fixture(name="valid_scraper_env")
def valid_scraper_env_() -> dict:
    """Raw env-var string dict mirroring pytest.ini values for ScraperParameters tests."""
    return {
        "environment": os.environ["ENVIRONMENT"],
        "city": os.environ["CITY"],
        "sites": os.environ["SITES"],
        "property_types": os.environ["PROPERTY_TYPES"],
        "upload_to_gcs": os.environ["UPLOAD_TO_GCS"],
        "start_page": os.environ["START_PAGE"],
        "max_page": os.environ["MAX_PAGE"],
        "version": os.environ.get("VERSION", "test"),
    }


@pytest.fixture(name="scraper_params")
def scraper_params_(env: Environment, expected_city: str) -> ScraperParameters:
    """ScraperParameters scoped to a single (site, property_type) pair for entrypoint tests."""
    return ScraperParameters.model_validate(
        {
            "environment": env,
            "city": expected_city,
            "sites": "vivareal",
            "property_types": "apartment",
            "upload_to_gcs": True,
            "start_page": 1,
            "max_page": None,
            "version": "test",
        }
    )


@pytest.fixture(name="scraper_params_no_upload")
def scraper_params_no_upload_(env: Environment, expected_city: str) -> ScraperParameters:
    """ScraperParameters with upload_to_gcs=False for GCS-skip-path tests."""
    return ScraperParameters.model_validate(
        {
            "environment": env,
            "city": expected_city,
            "sites": "vivareal",
            "property_types": "apartment",
            "upload_to_gcs": False,
            "start_page": 1,
            "max_page": None,
            "version": "test",
        }
    )


@pytest.fixture(name="scraper_params_with_max_page")
def scraper_params_with_max_page_(env: Environment, expected_city: str) -> ScraperParameters:
    """ScraperParameters with max_page=1 for loop-termination tests."""
    return ScraperParameters.model_validate(
        {
            "environment": env,
            "city": expected_city,
            "sites": "vivareal",
            "property_types": "apartment",
            "upload_to_gcs": True,
            "start_page": 1,
            "max_page": 1,
            "version": "test",
        }
    )


@pytest.fixture(name="valid_bronze_env")
def valid_bronze_env_() -> dict:
    """Field dict mirroring pytest.ini values for BronzeParameters tests."""
    max_page_raw = int(os.environ["MAX_PAGE"])
    return {
        "environment": os.environ["ENVIRONMENT"],
        "city": os.environ["CITY"],
        "sites": os.environ["SITES"],
        "property_types": os.environ["PROPERTY_TYPES"],
        "upload_to_bq": os.environ["UPLOAD_TO_BQ"],
        "file_date": "2026-01-01",
        "version": os.environ.get("VERSION", "test"),
        "start_page": int(os.environ["START_PAGE"]),
        "max_page": max_page_raw if max_page_raw > 0 else None,
    }


@pytest.fixture(name="bronze_params")
def bronze_params_(valid_bronze_env: dict) -> BronzeParameters:
    """BronzeParameters scoped to a single-date load run."""
    return BronzeParameters.model_validate(valid_bronze_env)


@pytest.fixture(name="bronze_table")
def bronze_table_(env: Environment) -> BronzeListingsTable:
    """BronzeListingsTable descriptor bound to the dev environment."""
    return BronzeListingsTable(env=env, project="test-project")


@pytest.fixture(name="audit_metadata")
def audit_metadata_() -> AuditMetadata:
    """AuditMetadata with fixed test timestamps."""
    return AuditMetadata(
        version_id="test",
        ins_ts="2026-01-01T00:00:00Z",
        upd_ts="2026-01-01T00:00:00Z",
    )


@pytest.fixture(name="source_metadata")
def source_metadata_(scraper_bucket: ScraperBucket) -> BronzeListingsTable.SourceMetadata:
    """SourceMetadata derived from the canonical scraper_bucket fixture."""
    return BronzeListingsTable.SourceMetadata(
        blob=f"{scraper_bucket.prefix}/2026-01-01T00:00:00Z.json",
        site_name=scraper_bucket.site,
        city_name=scraper_bucket.city,
        property_type_cat=scraper_bucket.property_type,
        page_num=scraper_bucket.page,
        executed_at_ts="2026-01-01T00:00:00Z",
    )


@pytest.fixture(name="raw_listing")
def raw_listing_() -> dict:
    """Minimal raw listing dict as scraped from the source site."""
    return {
        "@id": "12345",
        "@type": "Apartment",
        "name": "Test Apartment",
        "url": "https://example.com/listing/12345",
        "description": "A test listing.",
        "petsAllowed": False,
        "numberOfRooms": 2,
        "numberOfBedrooms": 2,
        "numberOfBathroomsTotal": 1,
        "address": {
            "streetAddress": "Rua Teste",
            "addressLocality": "Macaé",
            "addressRegion": "RJ",
            "addressCountry": "BR",
        },
        "floorSize": {"value": 60, "unitCode": "M2"},
        "image": ["https://example.com/img1.jpg"],
        "amenityFeature": [{"name": "Amenity", "value": "Pool"}],
        "offers": {
            "price": 2000,
            "priceCurrency": "BRL",
            "availability": "https://schema.org/InStock",
            "potentialAction": {
                "target": "https://example.com/listing/12345",
                "priceSpecification": {"price": 2000, "priceCurrency": "BRL"},
            },
            "propertyValue": {"name": "Condominium Fee", "value": 300, "unitText": "BRL/month"},
        },
    }
