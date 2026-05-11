"""Scraper package public API."""

from app.data.scrapers.settings import City
from app.data.scrapers.sites.viva_real import VivaRealScraper
from app.data.scrapers.sites.zap_imoveis import ZapImoveisScraper

__all__ = ["City", "VivaRealScraper", "ZapImoveisScraper"]
