"""Test the ScraperBucket descriptor for GCS-backed scraper output."""

from datetime import datetime, timezone

import pytest
from pytest_mock import MockerFixture

from app.data.gcs import ScraperBucket
from app.utils.utils import Environment, FileExtensions


def test_scraper_bucket_name(scraper_bucket: ScraperBucket) -> None:
    """Test ScraperBucket.name returns the fixed scraper-rentals-data bucket name."""
    assert scraper_bucket.name == "scraper-rentals-data"


def test_scraper_bucket_prefix(
    scraper_bucket: ScraperBucket, env: Environment, expected_city: str
) -> None:
    """Test ScraperBucket.prefix joins env/site/city/property_type/page in order."""
    assert scraper_bucket.prefix == f"{env}/vivareal/{expected_city}/apartment/1"


def test_blob_name_joins_prefix_filename_and_extension(
    scraper_bucket: ScraperBucket, file_extension: FileExtensions
) -> None:
    """Test blob_name renders prefix/filename.extension as a POSIX path."""
    assert (
        scraper_bucket.blob_name(filename="2026-01-01T00-00-00Z", extension=file_extension)
        == f"{scraper_bucket.prefix}/2026-01-01T00-00-00Z.{file_extension}"
    )


def test_glob_pattern_formats_to_correct_glob(scraper_bucket: ScraperBucket) -> None:
    """Test glob_pattern.format produces a valid GCS glob for a given date and extension."""
    pattern = scraper_bucket.glob_pattern.format(
        prefix=scraper_bucket.prefix,
        file_date="2026-01-01",
        extension="json",
    )
    assert pattern == f"{scraper_bucket.prefix}/2026-01-01T*.json"


def test_latest_blob_returns_most_recently_updated(
    scraper_bucket: ScraperBucket, mocker: MockerFixture
) -> None:
    """Test latest_blob returns the blob with the highest updated timestamp."""
    older = mocker.MagicMock()
    older.updated = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    newer = mocker.MagicMock()
    newer.updated = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    gcs_client = mocker.MagicMock()
    gcs_client.list_blobs.return_value = iter([older, newer])
    result = scraper_bucket.latest_blob(gcs_client, file_date="2026-01-01", extension="json")
    assert result is newer


def test_latest_blob_returns_none_when_no_blobs_match(
    scraper_bucket: ScraperBucket, mocker: MockerFixture
) -> None:
    """Test latest_blob returns None when list_blobs yields no results."""
    gcs_client = mocker.MagicMock()
    gcs_client.list_blobs.return_value = iter([])
    result = scraper_bucket.latest_blob(gcs_client, file_date="2026-01-01", extension="json")
    assert result is None


def test_latest_blob_passes_formatted_glob_to_list_blobs(
    scraper_bucket: ScraperBucket, mocker: MockerFixture
) -> None:
    """Test latest_blob calls list_blobs with the correctly formatted match_glob."""
    gcs_client = mocker.MagicMock()
    gcs_client.list_blobs.return_value = iter([])
    scraper_bucket.latest_blob(gcs_client, file_date="2026-01-01", extension="json")
    expected_glob = f"{scraper_bucket.prefix}/2026-01-01T*.json"
    gcs_client.list_blobs.assert_called_once_with(scraper_bucket.name, match_glob=expected_glob)


@pytest.mark.parametrize("bad_param", ["", " "])
def test_latest_blob_with_empty_extension_uses_glob_literally(
    scraper_bucket: ScraperBucket, mocker: MockerFixture, bad_param: str
) -> None:
    """Test latest_blob passes the extension through without validation."""
    gcs_client = mocker.MagicMock()
    gcs_client.list_blobs.return_value = iter([])
    scraper_bucket.latest_blob(gcs_client, file_date="2026-01-01", extension=bad_param)
    _, kwargs = gcs_client.list_blobs.call_args
    assert bad_param in kwargs["match_glob"]
