"""Bucket descriptors for GCS-backed storage targets."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import PurePosixPath

from app.utils import Environment, FileExtensions


@dataclass(frozen=True, kw_only=True)
class Bucket(ABC):
    """
    Env-scoped GCS bucket descriptor. Subclasses bind a concrete
    :attr:`name` and a :attr:`prefix` layout.

    ----------
    Parameters
    ----------
    env : Environment
        Deployment environment that scopes the object-key prefix.
    """

    env: Environment

    @property
    @abstractmethod
    def name(self) -> str:
        """GCS bucket name to upload to."""

    @property
    @abstractmethod
    def prefix(self) -> str:
        """Object-key prefix under :attr:`name`."""

    def blob_name(self, *, filename: str, extension: FileExtensions) -> str:
        """
        Build a fully-qualified blob name by joining :attr:`prefix` with
        ``filename.extension``.

        ----------
        Parameters
        ----------
        filename : str
            Base filename without extension.
        extension : FileExtensions
            File extension to append.

        ----------
        Returns
        ----------
        str
            POSIX-style object key
            (e.g. ``"dev/vivareal/macae/house/2026-01-01T00-00-00Z.json"``).
        """
        return str(PurePosixPath(self.prefix) / f"{filename}.{extension}")


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

    @property
    def name(self) -> str:
        """Fixed bucket name holding all scraped listings."""
        return "scraper-rentals-data"

    @property
    def prefix(self) -> str:
        """Object-key prefix ``<env>/<site>/<city>/<property_type>``."""
        return str(PurePosixPath(self.env) / self.site / self.city / self.property_type)
