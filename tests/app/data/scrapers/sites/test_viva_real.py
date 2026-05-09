"""Test VivaReal-specific bindings and URL composition for the inherited `set_url`."""

from app.data.scrapers.settings import City, PropertyTypes
from app.data.scrapers.sites.base import SiteScraper
from app.data.scrapers.sites.viva_real import (
    PROPERTY_TYPES_VIVA_REAL,
    URL_VIVA_REAL,
    VivaRealScraper,
)


def test_module_constants() -> None:
    """Test the module-level VivaReal constants are bound to the expected slugs and URL."""
    assert isinstance(PROPERTY_TYPES_VIVA_REAL, PropertyTypes)
    assert PROPERTY_TYPES_VIVA_REAL.apartment == "apartamento_residencial"
    assert PROPERTY_TYPES_VIVA_REAL.house == "casa_residencial"
    assert URL_VIVA_REAL == "https://www.vivareal.com.br/aluguel/{uf}/{city}/{property_type}/"


def test_inheritance_and_class_vars() -> None:
    """Test VivaRealScraper inherits SiteScraper and binds the expected class vars."""
    assert issubclass(VivaRealScraper, SiteScraper)
    assert VivaRealScraper._PROPERTY_TYPES is PROPERTY_TYPES_VIVA_REAL  # pylint: disable=w0212
    assert VivaRealScraper._URL_TEMPLATE == URL_VIVA_REAL  # pylint: disable=w0212


def test_set_url_apartment_renders_vivareal_url() -> None:
    """Test set_url renders VivaReal's apartment URL."""
    scraper = VivaRealScraper(city=City.MACAE).set_url("apartment")
    assert scraper.url == "https://www.vivareal.com.br/aluguel/rj/macae/apartamento_residencial/"


def test_set_url_house_renders_vivareal_url() -> None:
    """Test set_url renders VivaReal's house URL."""
    scraper = VivaRealScraper(city=City.MACAE).set_url("house")
    assert scraper.url == "https://www.vivareal.com.br/aluguel/rj/macae/casa_residencial/"
