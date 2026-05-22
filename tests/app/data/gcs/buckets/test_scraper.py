"""Tests for the ScraperBucket GCS bucket descriptor."""

from app.data.gcs import ScraperBucket
from app.utils import Environment


def test_scraper_bucket_name(scraper_bucket: ScraperBucket) -> None:
    """Test ScraperBucket.name returns the fixed scraper-rentals-data bucket name."""
    assert scraper_bucket.name == "scraper-rentals-data"


def test_scraper_bucket_prefix(
    scraper_bucket: ScraperBucket, env: Environment, expected_city: str
) -> None:
    """Test ScraperBucket.prefix joins env/site/city/property_type/page in order."""
    assert scraper_bucket.prefix == f"{env}/vivareal/{expected_city}/apartment/1"


def test_glob_pattern_formats_to_correct_glob(scraper_bucket: ScraperBucket) -> None:
    """Test glob_pattern.format produces a valid GCS glob for a given date and extension."""
    pattern = scraper_bucket.glob_pattern.format(filename="2026-01-01", extension="json")
    assert pattern == "2026-01-01T*.json"
