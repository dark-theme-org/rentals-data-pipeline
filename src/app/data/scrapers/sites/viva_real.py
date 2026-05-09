"""VivaReal site scraper."""

from app.data.scrapers.settings import PropertyTypes
from app.data.scrapers.sites.base import SiteScraper

PROPERTY_TYPES_VIVA_REAL = PropertyTypes(
    apartment="apartamento_residencial", house="casa_residencial"
)

URL_VIVA_REAL: str = "https://www.vivareal.com.br/aluguel/{uf}/{city}/{property_type}/"


class VivaRealScraper(SiteScraper):
    """
    :class:`SiteScraper` bound to VivaReal's URL pattern.
    Inherits the search parameters from the base class.
    """

    _PROPERTY_TYPES = PROPERTY_TYPES_VIVA_REAL
    _URL_TEMPLATE = URL_VIVA_REAL
