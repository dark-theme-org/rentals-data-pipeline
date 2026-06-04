"""Abstract GCS bucket descriptor."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import PurePosixPath

from google.cloud.storage import Blob, Client


@dataclass(kw_only=True)
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

    @property
    @abstractmethod
    def glob_pattern(self) -> str:
        """Build a GCS glob pattern to match blobs."""

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

    def latest_blob(self, gcs_client: Client, **kwargs: str) -> Blob | None:
        """
        Return the most recently updated blob whose name matches
        :attr:`glob_pattern` formatted with ``prefix=self.prefix`` and any
        additional ``kwargs`` required by the concrete pattern.

        ----------
        Parameters
        ----------
        gcs_client : Client
            Authenticated GCS client used to list blobs.
        **kwargs : str
            Pattern-specific placeholders forwarded to
            ``glob_pattern.format(prefix=self.prefix, **kwargs)``.

        ----------
        Returns
        ----------
        Blob | None
            Most recently updated matching blob, or ``None`` if none found.
        """
        return max(
            gcs_client.list_blobs(
                self.name,
                prefix=self.prefix,
                match_glob=self.glob_pattern.format(**kwargs),
            ),
            key=lambda b: b.updated,  # type: ignore
            default=None,
        )
