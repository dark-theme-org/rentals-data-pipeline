"""ZapImoveis site scraper."""

from app.data.scrapers.settings import PropertyTypes
from app.data.scrapers.sites.base import SiteScraper

PROPERTY_TYPES_ZAP_IMOVEIS = PropertyTypes(apartment="apartamentos", house="casas")

URL_ZAP_IMOVEIS: str = "https://www.zapimoveis.com.br/aluguel/{property_type}/{uf}+{city}/"


class ZapImoveisScraper(SiteScraper):
    """
    :class:`SiteScraper` bound to ZapImoveis's URL pattern.
    Inherits the search parameters from the base class.
    """

    _PROPERTY_TYPES = PROPERTY_TYPES_ZAP_IMOVEIS
    _URL_TEMPLATE = URL_ZAP_IMOVEIS
