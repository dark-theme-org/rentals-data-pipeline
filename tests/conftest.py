"""Project-wide pytest fixtures shared across the test suite."""

import json

import pytest
from pytest_mock import MockerFixture


@pytest.fixture(name="expected_city")
def expected_city_() -> str:
    """Canonical lowercase city slug expected for `City.MACAE`."""
    return "macae"


@pytest.fixture(name="expected_uf")
def expected_uf_() -> str:
    """Canonical two-letter UF code expected for `UF.RJ`."""
    return "rj"


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
