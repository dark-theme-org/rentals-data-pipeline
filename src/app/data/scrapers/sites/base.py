"""Base class for site-specific scrapers."""

import json
import logging
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import ClassVar, Self

from bs4 import BeautifulSoup
from curl_cffi import requests
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from app.data.scrapers.settings import CITIES_UF, UF, City, PropertyTypes

logger = logging.getLogger(__name__)


@dataclass
class SiteScraper:
    """
    Site-agnostic base for real-estate listing search targets. Subclasses
    bind a `_URL_TEMPLATE` and a `_PROPERTY_TYPES` class variable to a
    site-specific URL pattern.

    ----------
    Parameters
    ----------
    city : City
        Target city (e.g. ``City.MACAE``).
    """

    city: City
    soup: BeautifulSoup | None = field(default=None, init=False)
    url: str | None = field(default=None, init=False)

    _PROPERTY_TYPES: ClassVar[PropertyTypes]
    _SITE_NAME: ClassVar[str]
    _URL_TEMPLATE: ClassVar[str]

    @property
    def uf(self) -> UF:
        """
        Resolved UF for the supplied :attr:`city`.

        ----------
        Returns
        ----------
        UF:
            UF code (e.g. ``UF.RJ``).

        ----------
        Raises
        ----------
        KeyError
            If :attr:`city` is not registered in :data:`CITIES_UF`.
        """
        return CITIES_UF[self.city]

    @classmethod
    def get_site_name(cls) -> str:
        """Return the site identifier bound to this scraper class."""
        return cls._SITE_NAME

    def set_url(self, property_type: str) -> Self:
        """
        Format ``_URL_TEMPLATE`` with :attr:`uf`, :attr:`city` and the
        site-specific slug looked up on ``_PROPERTY_TYPES`` for the given
        ``property_type``, store the result on :attr:`url`, and return
        ``self`` so the call can be chained right after construction
        (e.g. ``VivaRealScraper(City(CITY)).set_url("apartment")``).

        ----------
        Parameters
        ----------
        property_type : str
            Canonical property-type identifier (e.g. ``"apartment"``,
            ``"house"``). Must match an attribute of ``_PROPERTY_TYPES``.

        ----------
        Returns
        ----------
        Self
            The same scraper instance, with :attr:`url` populated.

        ----------
        Raises
        ----------
        AttributeError
            If ``property_type`` does not match an attribute on
            ``_PROPERTY_TYPES``.
        """
        self.url = self._URL_TEMPLATE.format(
            site=self._SITE_NAME,
            uf=str(self.uf),
            city=str(self.city),
            property_type=getattr(self._PROPERTY_TYPES, property_type),
        )
        return self

    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        stop=stop_after_attempt(5),
        wait=wait_random_exponential(multiplier=1, min=2, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),  # type: ignore[arg-type]
        reraise=True,
    )
    def fetch_and_parse_html(self, page: int = 1, timeout: int = 5) -> Self | None:
        """
        Fetch :attr:`url` and store the parsed ``BeautifulSoup`` document on
        :attr:`soup`.

        Only HTTP ``200 OK`` is treated as success. ``404 Not Found`` returns
        ``None`` and signals the caller that no more pages are available.
        Any other non-200 status raises :class:`requests.HTTPError`. Retries
        up to three times with exponential backoff on
        :class:`requests.RequestException` (connection errors, timeouts, the
        ``HTTPError`` raised here for non-200/non-404 responses); other
        exceptions propagate immediately.

        ----------
        Parameters
        ----------
        page : int, default 1
            Page number passed to the site as the ``pagina`` query parameter.
        timeout : int, default 5
            Per-attempt timeout in seconds passed to :func:`requests.get`.

        ----------
        Returns
        ----------
        Self
            The same scraper instance, with :attr:`soup` populated.
        None
            If the response status code is ``404 Not Found``, indicating
            there are no more pages to scrape.

        ----------
        Raises
        ----------
        ValueError
            If :attr:`url` has not been set. Call :meth:`set_url` first.
        requests.HTTPError
            If the response status code is anything other than ``200 OK`` or
            ``404 Not Found``, after the configured retries are exhausted.
        requests.RequestException
            If the request keeps failing after the configured retries.
        """
        if self.url is None:
            raise ValueError(
                "URL is not set. Call `set_url(property_type)` before `fetch_and_parse_html()`."
            )
        try:
            logger.info(f"[{self.__class__.__name__}] Fetching '{self.url}' for page={page} ...")
            headers = {
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
                "Referer": f"{self.url}?pagina={page - 1}" if page > 1 else self.url,
            }
            response = requests.get(
                self.url,
                params={"pagina": page},
                headers=headers,
                timeout=timeout,
                impersonate="chrome120",
            )
            if response.status_code == HTTPStatus.NOT_FOUND:
                logger.warning(
                    f"[{self.__class__.__name__}] URL '{self.url}' for page={page} result in "
                    f"status_code={response.status_code}. Returning None..."
                )
                return None
            if response.status_code != HTTPStatus.OK:
                raise requests.exceptions.HTTPError(
                    f"Expected {HTTPStatus.OK}, got {response.status_code} from '{self.url}' "
                    f"(page={page}).",
                    response=response,
                )
            logger.info(
                f"[{self.__class__.__name__}] Succesfull request to '{self.url}' for page={page}!"
            )
        except requests.exceptions.RequestException:
            logger.exception(
                f"[{self.__class__.__name__}] Failed to fetch '{self.url}' for page={page}."
            )
            raise
        logger.info(f"[{self.__class__.__name__}] Parsing HTML ...")
        self.soup = BeautifulSoup(response.text, "html.parser")
        logger.info(f"[{self.__class__.__name__}] HTML successfully parsed!")
        return self

    def extract_properties(self) -> dict[str, dict]:
        """
        Read the JSON-LD blocks embedded in :attr:`soup`, locate the
        ``ItemList`` block, and return every listing it contains indexed
        by its ``@id``.

        ----------
        Returns
        ----------
        Dict[str, Dict]
            Mapping ``listing @id -> listing payload``.

        ----------
        Raises
        ----------
        ValueError
            If :attr:`soup` has not been parsed yet (call
            :meth:`fetch_and_parse_html` first), or if no ``ItemList``
            JSON-LD block is present in the page.
        json.JSONDecodeError
            If a ``<script type="application/ld+json">`` block contains
            malformed JSON.
        """
        if self.soup is None:
            raise ValueError(
                "HTML is not parsed. Call `fetch_and_parse_html()` before `extract_listings()`."
            )
        logger.info(f"[{self.__class__.__name__}] Extracting list of items ...")
        logger.info(
            f"[{self.__class__.__name__}] Collecting every JSON-LD block embedded in the page ..."
        )
        ld_blocks: list[dict] = [
            json.loads(tag.string)
            for tag in self.soup.find_all("script", type="application/ld+json")
            if tag.string
        ]
        logger.info(
            f"[{self.__class__.__name__}] Locating `ItemList` block and "
            "index each listing by its `@id` ..."
        )
        try:
            item_list = next(block for block in ld_blocks if block.get("@type") == "ItemList")
        except StopIteration as exc:
            raise ValueError(
                f"No `ItemList` JSON-LD block found in parsed HTML at '{self.url}'."
            ) from exc
        listings: dict[str, dict] = {
            element["item"]["@id"]: element["item"] for element in item_list["itemListElement"]
        }
        logger.info(f"[{self.__class__.__name__}] Succesfully extracted '{len(listings)}' items!")
        return listings
