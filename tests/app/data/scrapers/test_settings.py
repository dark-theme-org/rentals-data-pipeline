"""Test enums, mapping and frozen dataclass exposed by the scrapers settings module."""

import dataclasses

import pytest

from app.data.scrapers.settings import CITIES_UF, UF, City, PropertyTypes


def test_city_enum_values(expected_city: str) -> None:
    """Test City enum exposes the expected slug values."""
    assert City.MACAE == expected_city


def test_uf_enum_values(expected_uf: str) -> None:
    """Test UF enum exposes the expected two-letter codes."""
    assert UF.RJ == expected_uf


def test_cities_uf_mapping() -> None:
    """Test CITIES_UF maps every supported city to a registered UF."""
    assert CITIES_UF[City.MACAE] is UF.RJ
    for city, uf in CITIES_UF.items():
        assert isinstance(city, City)
        assert isinstance(uf, UF)


def test_property_types_construction(property_apartment: str, property_house: str) -> None:
    """Test PropertyTypes can be constructed with apartment and house slugs."""
    pt = PropertyTypes(apartment=property_apartment, house=property_house)
    assert pt.apartment == property_apartment
    assert pt.house == property_house


def test_property_types_is_frozen(property_apartment: str, property_house: str) -> None:
    """Test PropertyTypes raises on attribute mutation."""
    pt = PropertyTypes(apartment=property_apartment, house=property_house)
    with pytest.raises(dataclasses.FrozenInstanceError):
        pt.apartment = "other"  # type: ignore[misc]
