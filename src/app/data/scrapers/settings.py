"""Shared types and constants for scraping configuration."""

from dataclasses import dataclass
from enum import StrEnum


class City(StrEnum):
    """Supported city slugs (lowercase, hyphen-separated, no diacritics)."""

    MACAE = "macae"


class UF(StrEnum):
    """Supported Brazilian state codes (lowercase, two-letter)."""

    RJ = "rj"


CITIES_UF: dict[City, UF] = {City.MACAE: UF.RJ}


@dataclass(frozen=True)
class PropertyTypes:
    """
    Real-estate property category bound to a site-specific URL slug.

    ----------
    Parameters
    ----------
    apartment : str
        Identifier category for 'apartment' properties.
    house : str
        Identifier category for 'house' properties.
    """

    apartment: str
    house: str
