"""Test the base `SiteScraper` URL composition, fetch retry policy and JSON-LD extraction."""

import json

import pytest
from bs4 import BeautifulSoup
from curl_cffi import requests
from pytest_mock import MockerFixture

from app.data.scrapers.settings import City, PropertyTypes
from app.data.scrapers.sites.base import SiteScraper


@pytest.fixture(name="fast_retry")
def fast_retry_(mocker: MockerFixture) -> None:
    """No-op `tenacity` sleep so retry-decorated calls don't actually wait."""
    mocker.patch("tenacity.nap.time.sleep")


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


_STUB_URL_TEMPLATE = "https://example.com/{uf}/{city}/{property_type}/"
_REQUESTS_GET = "app.data.scrapers.sites.base.requests.get"


@pytest.fixture(name="stub_scraper")
def stub_scraper_(
    property_apartment: str,
    property_house: str,
    monkeypatch: pytest.MonkeyPatch,
) -> SiteScraper:
    """A `SiteScraper` instance with stub class-level templates patched in."""
    monkeypatch.setattr(
        SiteScraper,
        "_PROPERTY_TYPES",
        PropertyTypes(apartment=property_apartment, house=property_house),
        raising=False,
    )
    monkeypatch.setattr(SiteScraper, "_SITE_NAME", "stub", raising=False)
    monkeypatch.setattr(SiteScraper, "_URL_TEMPLATE", _STUB_URL_TEMPLATE, raising=False)
    return SiteScraper(city=City.MACAE)


def test_get_site_name_returns_class_var(stub_scraper: SiteScraper) -> None:
    """Test get_site_name returns the _SITE_NAME class variable."""
    assert stub_scraper.get_site_name() == "stub"


def test_set_url_renders_url_and_returns_self(
    stub_scraper: SiteScraper,
    expected_city: str,
    expected_uf: str,
    property_apartment: str,
) -> None:
    """Test `set_url` formats the URL with the selected slug and returns self for chaining."""
    result = stub_scraper.set_url("apartment")
    assert result is stub_scraper
    assert stub_scraper.url == _STUB_URL_TEMPLATE.format(
        uf=expected_uf, city=expected_city, property_type=property_apartment
    )


def test_set_url_raises_for_unknown_property_type(stub_scraper: SiteScraper) -> None:
    """Test `set_url` raises `AttributeError` when the property type is not declared."""
    with pytest.raises(AttributeError):
        stub_scraper.set_url("commercial")


def test_fetch_and_parse_html_raises_when_url_not_set(stub_scraper: SiteScraper) -> None:
    """Test `fetch_and_parse_html` raises `ValueError` if the URL was not set."""
    with pytest.raises(ValueError, match="URL is not set"):
        stub_scraper.fetch_and_parse_html()


def test_fetch_and_parse_html_success(
    stub_scraper: SiteScraper, mocker: MockerFixture, html_with_item_list: str
) -> None:
    """Test `fetch_and_parse_html` populates `soup` on a 200 response and returns self."""
    response = mocker.MagicMock(status_code=200, text=html_with_item_list)
    mocker.patch(_REQUESTS_GET, return_value=response)

    result = stub_scraper.set_url("apartment").fetch_and_parse_html()

    assert result is stub_scraper
    assert isinstance(stub_scraper.soup, BeautifulSoup)


def test_fetch_and_parse_html_passes_page_as_pagina_query_param(
    stub_scraper: SiteScraper, mocker: MockerFixture, html_with_item_list: str
) -> None:
    """Test `fetch_and_parse_html` passes the page number as the `pagina` query parameter."""
    response = mocker.MagicMock(status_code=200, text=html_with_item_list)
    get = mocker.patch(_REQUESTS_GET, return_value=response)

    stub_scraper.set_url("apartment").fetch_and_parse_html(page=3)

    _, kwargs = get.call_args
    assert kwargs["params"] == {"pagina": 3}


def test_fetch_and_parse_html_sets_referer_to_url_on_page_1(
    stub_scraper: SiteScraper, mocker: MockerFixture, html_with_item_list: str
) -> None:
    """Test `fetch_and_parse_html` sets Referer to the base URL on the first page."""
    response = mocker.MagicMock(status_code=200, text=html_with_item_list)
    get = mocker.patch(_REQUESTS_GET, return_value=response)

    stub_scraper.set_url("apartment").fetch_and_parse_html(page=1)

    _, kwargs = get.call_args
    assert kwargs["headers"]["Referer"] == stub_scraper.url


def test_fetch_and_parse_html_sets_referer_to_previous_page_when_page_gt_1(
    stub_scraper: SiteScraper, mocker: MockerFixture, html_with_item_list: str
) -> None:
    """Test `fetch_and_parse_html` sets Referer to url?pagina=N-1 on subsequent pages."""
    response = mocker.MagicMock(status_code=200, text=html_with_item_list)
    get = mocker.patch(_REQUESTS_GET, return_value=response)

    stub_scraper.set_url("apartment").fetch_and_parse_html(page=3)

    _, kwargs = get.call_args
    assert kwargs["headers"]["Referer"] == f"{stub_scraper.url}?pagina=2"


def test_fetch_and_parse_html_returns_none_on_404(
    stub_scraper: SiteScraper, mocker: MockerFixture
) -> None:
    """Test `fetch_and_parse_html` returns None when the server responds with 404."""
    response = mocker.MagicMock(status_code=404)
    mocker.patch(_REQUESTS_GET, return_value=response)

    result = stub_scraper.set_url("apartment").fetch_and_parse_html()

    assert result is None


@pytest.mark.usefixtures("fast_retry")
def test_fetch_and_parse_html_retries_then_succeeds(
    stub_scraper: SiteScraper, mocker: MockerFixture, html_with_item_list: str
) -> None:
    """Test `fetch_and_parse_html` retries on transient `RequestException` then succeeds."""
    ok_response = mocker.MagicMock(status_code=200, text=html_with_item_list)
    get = mocker.patch(
        _REQUESTS_GET,
        side_effect=[requests.exceptions.ConnectionError("flaky"), ok_response],
    )

    stub_scraper.set_url("apartment").fetch_and_parse_html()

    assert get.call_count == 2
    assert isinstance(stub_scraper.soup, BeautifulSoup)


@pytest.mark.usefixtures("fast_retry")
def test_fetch_and_parse_html_raises_http_error_after_retries(
    stub_scraper: SiteScraper, mocker: MockerFixture
) -> None:
    """Test `fetch_and_parse_html` raises `HTTPError` after exhausting all 5 retry attempts."""
    response = mocker.MagicMock(status_code=503, text="boom")
    get = mocker.patch(_REQUESTS_GET, return_value=response)

    with pytest.raises(requests.exceptions.HTTPError):
        stub_scraper.set_url("apartment").fetch_and_parse_html()

    assert get.call_count == 5


def test_extract_properties_raises_when_soup_not_parsed(stub_scraper: SiteScraper) -> None:
    """Test `extract_properties` raises `ValueError` before `fetch_and_parse_html` runs."""
    with pytest.raises(ValueError, match="HTML is not parsed"):
        stub_scraper.extract_properties()


def test_extract_properties_returns_listings_indexed_by_id(
    stub_scraper: SiteScraper, html_with_item_list: str, item_list_payload: dict
) -> None:
    """Test `extract_properties` indexes every `ItemList` listing by its `@id`."""
    stub_scraper.soup = BeautifulSoup(html_with_item_list, "html.parser")

    listings = stub_scraper.extract_properties()

    assert isinstance(listings, dict)
    assert len(listings) == len(item_list_payload["itemListElement"])
    for element in item_list_payload["itemListElement"]:
        assert listings[element["item"]["@id"]] == element["item"]


def test_extract_properties_raises_when_no_item_list(
    stub_scraper: SiteScraper, html_without_item_list: str
) -> None:
    """Test `extract_properties` raises `ValueError` when no `ItemList` block is present."""
    stub_scraper.soup = BeautifulSoup(html_without_item_list, "html.parser")
    with pytest.raises(ValueError, match="No `ItemList` JSON-LD block"):
        stub_scraper.extract_properties()


def test_extract_properties_raises_on_bad_json(
    stub_scraper: SiteScraper, html_with_bad_json: str
) -> None:
    """Test `extract_properties` raises `JSONDecodeError` on malformed JSON-LD content."""
    stub_scraper.soup = BeautifulSoup(html_with_bad_json, "html.parser")
    with pytest.raises(json.JSONDecodeError):
        stub_scraper.extract_properties()
