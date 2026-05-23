"""Project-wide pytest fixtures shared across the test suite."""

import os

import pytest

from app.data.bigquery import AuditMetadata, BronzeListingsTable
from app.data.gcs import ScraperBucket
from app.data.scrapers.sites.viva_real import SITE_NAME_VIVA_REAL
from app.utils import CloudSettings


@pytest.fixture(name="env")
def env_() -> str:
    """Deployment environment string read from the ENVIRONMENT pytest.ini variable."""
    return os.environ["ENVIRONMENT"]


@pytest.fixture(name="expected_city")
def expected_city_() -> str:
    """City slug read from the CITY pytest.ini variable."""
    return os.environ["CITY"]


@pytest.fixture(name="expected_uf")
def expected_uf_() -> str:
    """Canonical two-letter UF code for `UF.RJ`."""
    return "rj"


@pytest.fixture(name="file_date")
def file_date_() -> str:
    """Scrape date string read from the FILE_DATE pytest.ini variable."""
    return os.environ["FILE_DATE"]


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


@pytest.fixture(name="scraper_bucket")
def scraper_bucket_(env: str, expected_city: str) -> ScraperBucket:
    """ScraperBucket bound to a canonical (env, site, city, property_type, page) tuple."""
    return ScraperBucket(
        env=env, site=SITE_NAME_VIVA_REAL, city=expected_city, property_type="apartment", page=1
    )


@pytest.fixture(name="audit_metadata")
def audit_metadata_(file_date: str) -> AuditMetadata:
    """AuditMetadata with fixed test timestamps derived from FILE_DATE."""
    ts = f"{file_date}T00:00:00Z"
    return AuditMetadata(version_id="test", ins_ts=ts, upd_ts=ts)


@pytest.fixture(name="bronze_table")
def bronze_table_(env: str) -> BronzeListingsTable:
    """BronzeListingsTable descriptor bound to the dev environment."""
    return BronzeListingsTable(env=env, project=CloudSettings.PROJECT_ID)


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
