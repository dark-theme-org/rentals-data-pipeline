"""Tests for the ScraperBucket GCS bucket descriptor."""

from app.data.gcs import ScraperBucket


def test_scraper_bucket_name(scraper_bucket: ScraperBucket) -> None:
    """Test ScraperBucket.name returns the fixed scraper-rentals-data bucket name."""
    assert scraper_bucket.name == "scraper-rentals-data"


def test_scraper_bucket_prefix(scraper_bucket: ScraperBucket, env: str, expected_city: str) -> None:
    """Test ScraperBucket.prefix joins env/site/city/property_type/page in order."""
    assert scraper_bucket.prefix == f"{env}/{scraper_bucket.site}/{expected_city}/apartment/1"


def test_glob_pattern_formats_to_correct_glob(
    scraper_bucket: ScraperBucket, file_date: str
) -> None:
    """Test glob_pattern.format produces a full-path GCS glob for a given date and extension."""
    pattern = scraper_bucket.glob_pattern.format(filename=file_date, extension="json")
    assert pattern == f"{scraper_bucket.prefix}/{file_date}T*.json"
