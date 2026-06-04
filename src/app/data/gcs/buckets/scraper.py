"""GCS bucket descriptor for scraped real-estate listings."""

from dataclasses import dataclass
from pathlib import PurePosixPath

from app.data.gcs.buckets.base import Bucket


@dataclass(kw_only=True)
class ScraperBucket(Bucket):
    """
    :class:`Bucket` for scraped real-estate listings. The prefix layout
    partitions blobs by ``env/site/city/property_type``.

    ----------
    Parameters
    ----------
    site : str
        Source site identifier (e.g. ``"vivareal"``).
    city : str
        City slug the listings belong to.
    property_type : str
        Canonical property-type identifier (e.g. ``"apartment"``).
    """

    site: str
    city: str
    property_type: str
    page: int

    @property
    def name(self) -> str:
        """Fixed bucket name holding all scraped listings."""
        return "scraper-rentals-data"

    @property
    def prefix(self) -> str:
        """Object-key prefix ``<env>/<site>/<city>/<property_type>/<page>``."""
        return str(
            PurePosixPath(self.env) / self.site / self.city / self.property_type / str(self.page)
        )

    @property
    def glob_pattern(self) -> str:
        """Pattern to match blobs for a given scraper run date."""
        return f"{self.prefix}/{{filename}}T*.{{extension}}"
