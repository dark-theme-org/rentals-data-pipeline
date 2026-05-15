"""Project-wide pytest fixtures shared across the test suite."""

import json

import pytest
from pytest_mock import MockerFixture

from app.utils import Environment, FileExtensions
from app.utils.gcs import ScraperBucket
from app.utils.validations import ScraperParameters


@pytest.fixture(name="env")
def env_() -> Environment:
    """Default deployment environment used by GCS-target tests."""
    return Environment.DEV


@pytest.fixture(name="file_extension")
def file_extension_() -> FileExtensions:
    """Default file extension for blob payloads."""
    return FileExtensions.JSON


@pytest.fixture(name="scraper_bucket")
def scraper_bucket_(env: Environment, expected_city: str) -> ScraperBucket:
    """ScraperBucket bound to a canonical (env, site, city, property_type) tuple."""
    return ScraperBucket(env=env, site="vivareal", city=expected_city, property_type="apartment")


@pytest.fixture(name="expected_city")
def expected_city_() -> str:
    """Canonical lowercase city slug expected for `City.MACAE`."""
    return "macae"


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


@pytest.fixture(name="valid_scraper_env")
def valid_scraper_env_() -> dict:
    """Raw env var dict for instantiating ScraperParameters via model_validate."""
    return {
        "environment": "dev",
        "city": "macae",
        "sites": "vivareal,zapimoveis",
        "property_types": "apartment,house",
    }


@pytest.fixture(name="scraper_params")
def scraper_params_() -> ScraperParameters:
    """ScraperParameters scoped to a single (site, property_type) pair for entrypoint tests."""
    return ScraperParameters.model_validate(
        {
            "environment": "dev",
            "city": "macae",
            "sites": "vivareal",
            "property_types": "apartment",
        }
    )
