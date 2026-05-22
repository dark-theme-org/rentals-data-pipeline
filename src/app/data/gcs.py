"""Bucket descriptors for GCS-backed storage targets."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import PurePosixPath

from google.cloud.storage import Blob, Client


@dataclass(frozen=True, kw_only=True)
class Bucket(ABC):
    """
    Env-scoped GCS bucket descriptor. Subclasses bind a concrete
    :attr:`name` and a :attr:`prefix` layout.

    ----------
    Parameters
    ----------
    env : str
        Deployment environment that scopes the object-key prefix.
    """

    env: str

    @property
    @abstractmethod
    def name(self) -> str:
        """GCS bucket name to upload to."""

    @property
    @abstractmethod
    def prefix(self) -> str:
        """Object-key prefix under :attr:`name`."""

    def blob_name(self, *, filename: str, extension: str) -> str:
        """
        Build a fully-qualified blob name by joining :attr:`prefix` with
        ``filename.extension``.

        ----------
        Parameters
        ----------
        filename : str
            Base filename without extension.
        extension : str
            File extension to append.

        ----------
        Returns
        ----------
        str
            POSIX-style object key
            (e.g. ``"dev/vivareal/macae/house/2026-01-01T00-00-00Z.json"``).
        """
        return str(PurePosixPath(self.prefix) / f"{filename}.{extension}")

    @property
    @abstractmethod
    def glob_pattern(self) -> str:
        """Build a GCS glob pattern to match blobs for a given scraper run date."""


@dataclass(frozen=True, kw_only=True)
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
        """Build a GCS glob pattern to match blobs for a given scraper run date."""
        return "{prefix}/{file_date}T*.{extension}"

    def latest_blob(
        self,
        gcs_client: Client,
        *,
        file_date: str,
        extension: str,
    ) -> Blob | None:
        """
        Return the most recently updated blob for the given scraper run date.

        Lists all blobs under :attr:`prefix` that match the glob for
        ``file_prefix`` and returns the one with the highest ``updated``
        timestamp, or ``None`` if no matching blob is found.

        ----------
        Parameters
        ----------
        gcs_client : Client
            Authenticated GCS client used to list blobs.
        file_date : str
            Scraper run date in ``YYYY-MM-DD`` format used as the blob
            filename prefix (e.g. ``"2026-01-01"``).
        extension : str
            File extension to match (e.g. ``"json"``).

        ----------
        Returns
        ----------
        Blob | None
            Most recently updated matching blob, or ``None`` if none found.
        """
        return max(
            gcs_client.list_blobs(
                self.name,
                match_glob=self.glob_pattern.format(
                    prefix=self.prefix, file_date=file_date, extension=extension
                ),
            ),
            key=lambda b: b.updated,  # type: ignore
            default=None,
        )
