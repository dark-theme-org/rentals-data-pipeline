"""GCS package public API."""

from app.data.gcs.buckets.base import Bucket
from app.data.gcs.buckets.scraper import ScraperBucket

__all__ = ["Bucket", "ScraperBucket"]
