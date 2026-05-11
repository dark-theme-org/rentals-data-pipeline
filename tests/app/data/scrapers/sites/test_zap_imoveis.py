"""Test ZapImoveis-specific bindings and URL composition for the inherited `set_url`."""

from app.data.scrapers.settings import City, PropertyTypes
from app.data.scrapers.sites.base import SiteScraper
from app.data.scrapers.sites.zap_imoveis import (
    PROPERTY_TYPES_ZAP_IMOVEIS,
    SITE_NAME_ZAP_IMOVEIS,
    URL_ZAP_IMOVEIS,
    ZapImoveisScraper,
)


def test_module_constants() -> None:
    """Test the module-level ZapImoveis constants are bound to the expected slugs and URL."""
    assert isinstance(PROPERTY_TYPES_ZAP_IMOVEIS, PropertyTypes)
    assert PROPERTY_TYPES_ZAP_IMOVEIS.apartment == "apartamentos"
    assert PROPERTY_TYPES_ZAP_IMOVEIS.house == "casas"
    assert SITE_NAME_ZAP_IMOVEIS == "zapimoveis"
    assert URL_ZAP_IMOVEIS == "https://www.{site}.com.br/aluguel/{property_type}/{uf}+{city}/"


def test_inheritance_and_class_vars() -> None:
    """Test ZapImoveisScraper inherits SiteScraper and binds the expected class vars."""
    assert issubclass(ZapImoveisScraper, SiteScraper)
    assert ZapImoveisScraper._PROPERTY_TYPES is PROPERTY_TYPES_ZAP_IMOVEIS  # pylint: disable=w0212
    assert ZapImoveisScraper._SITE_NAME == SITE_NAME_ZAP_IMOVEIS  # pylint: disable=w0212
    assert ZapImoveisScraper._URL_TEMPLATE == URL_ZAP_IMOVEIS  # pylint: disable=w0212


def test_set_url_apartment_renders_zapimoveis_url() -> None:
    """Test set_url renders ZapImoveis's apartment URL."""
    scraper = ZapImoveisScraper(city=City.MACAE).set_url("apartment")
    assert scraper.url == "https://www.zapimoveis.com.br/aluguel/apartamentos/rj+macae/"


def test_set_url_house_renders_zapimoveis_url() -> None:
    """Test set_url renders ZapImoveis's house URL."""
    scraper = ZapImoveisScraper(city=City.MACAE).set_url("house")
    assert scraper.url == "https://www.zapimoveis.com.br/aluguel/casas/rj+macae/"
