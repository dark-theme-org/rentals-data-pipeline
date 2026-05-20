"""Table descriptors for BigQuery-backed storage targets."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.utils import Environment

BRONZE_DATASET: str = "{env}_bronze"
DESTINATION_PATH: str = "{project}.{dataset}.{table}"


@dataclass(frozen=True, kw_only=True)
class Table(ABC):
    """
    Env-scoped BigQuery table descriptor. Subclasses bind a concrete
    :attr:`dataset` and :attr:`table`.

    ----------
    Parameters
    ----------
    env : str
        Deployment environment. Must be a valid :class:`~app.utils.Environment`
        value (``"dev"``, ``"test"``, ``"prod"``).
    project : str
        GCP project ID.
    """

    env: str
    project: str

    def __post_init__(self) -> None:
        Environment(self.env)

    @property
    @abstractmethod
    def dataset(self) -> str:
        """BigQuery dataset name."""

    @property
    @abstractmethod
    def table(self) -> str:
        """BigQuery table name."""

    @property
    def destination(self) -> str:
        """
        Fully-qualified BigQuery table reference.

        ----------
        Returns
        ----------
        str
            ``"<project>.<dataset>.<table>"``
            (e.g. ``"my-project.dev_bronze.listings"``).
        """
        return DESTINATION_PATH.format(
            project=self.project,
            dataset=self.dataset,
            table=self.table,
        )


@dataclass(frozen=True, kw_only=True)
class BronzeListingsTable(Table):
    """
    :class:`Table` for the Bronze layer of scraped real-estate listings.
    """

    @property
    def dataset(self) -> str:
        """Dataset name scoped by environment (e.g. ``"dev_bronze"``, ``"prod_bronze"``)."""
        return BRONZE_DATASET.format(env=self.env)

    @property
    def table(self) -> str:
        """Fixed table name for scraped listings."""
        return "listings"
