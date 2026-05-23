"""Tests for the Bucket abstract base class concrete methods."""

from datetime import datetime, timezone

import pytest
from pytest_mock import MockerFixture

from app.data.gcs import ScraperBucket
from app.utils import FileExtensions


def test_blob_name_joins_prefix_filename_and_extension(
    scraper_bucket: ScraperBucket, file_date: str
) -> None:
    """Test blob_name renders prefix/filename.extension as a POSIX path."""
    extension = FileExtensions.JSON
    filename = f"{file_date}T00-00-00Z"
    assert (
        scraper_bucket.blob_name(filename=filename, extension=extension)
        == f"{scraper_bucket.prefix}/{filename}.{extension}"
    )


def test_latest_blob_returns_most_recently_updated(
    scraper_bucket: ScraperBucket, mocker: MockerFixture, file_date: str
) -> None:
    """Test latest_blob returns the blob with the highest updated timestamp."""
    older = mocker.MagicMock()
    older.updated = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    newer = mocker.MagicMock()
    newer.updated = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    gcs_client = mocker.MagicMock()
    gcs_client.list_blobs.return_value = iter([older, newer])
    result = scraper_bucket.latest_blob(gcs_client, filename=file_date, extension="json")
    assert result is newer


def test_latest_blob_returns_none_when_no_blobs_match(
    scraper_bucket: ScraperBucket, mocker: MockerFixture, file_date: str
) -> None:
    """Test latest_blob returns None when list_blobs yields no results."""
    gcs_client = mocker.MagicMock()
    gcs_client.list_blobs.return_value = iter([])
    result = scraper_bucket.latest_blob(gcs_client, filename=file_date, extension="json")
    assert result is None


def test_latest_blob_passes_prefix_and_glob_to_list_blobs(
    scraper_bucket: ScraperBucket, mocker: MockerFixture, file_date: str
) -> None:
    """Test latest_blob calls list_blobs with prefix= and a correctly formatted match_glob."""
    gcs_client = mocker.MagicMock()
    gcs_client.list_blobs.return_value = iter([])
    scraper_bucket.latest_blob(gcs_client, filename=file_date, extension="json")
    gcs_client.list_blobs.assert_called_once_with(
        scraper_bucket.name, prefix=scraper_bucket.prefix, match_glob=f"{file_date}T*.json"
    )


@pytest.mark.parametrize("bad_param", ["", " "])
def test_latest_blob_with_empty_extension_uses_glob_literally(
    scraper_bucket: ScraperBucket, mocker: MockerFixture, file_date: str, bad_param: str
) -> None:
    """Test latest_blob passes the extension through without validation."""
    gcs_client = mocker.MagicMock()
    gcs_client.list_blobs.return_value = iter([])
    scraper_bucket.latest_blob(gcs_client, filename=file_date, extension=bad_param)
    _, kwargs = gcs_client.list_blobs.call_args
    assert bad_param in kwargs["match_glob"]
