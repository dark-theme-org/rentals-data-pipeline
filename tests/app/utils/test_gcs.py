"""Test the ScraperBucket descriptor for GCS-backed scraper output."""

from app.utils.gcs import ScraperBucket
from app.utils.utils import Environment, FileExtensions


def test_scraper_bucket_name(scraper_bucket: ScraperBucket) -> None:
    """Test ScraperBucket.name returns the fixed scraper-rentals-data bucket name."""
    assert scraper_bucket.name == "scraper-rentals-data"


def test_scraper_bucket_prefix(
    scraper_bucket: ScraperBucket, env: Environment, expected_city: str
) -> None:
    """Test ScraperBucket.prefix joins env/site/city/property_type in order."""
    assert scraper_bucket.prefix == f"{env}/vivareal/{expected_city}/apartment"


def test_blob_name_joins_prefix_filename_and_extension(
    scraper_bucket: ScraperBucket, file_extension: FileExtensions
) -> None:
    """Test blob_name renders prefix/filename.extension as a POSIX path."""
    assert (
        scraper_bucket.blob_name(filename="2026-01-01T00-00-00Z", extension=file_extension)
        == f"{scraper_bucket.prefix}/2026-01-01T00-00-00Z.{file_extension}"
    )
