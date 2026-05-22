"""Abstract BigQuery table descriptor and shared audit metadata."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from google.cloud import bigquery

from app.data.bigquery.settings import SQL_PATH
from app.utils import Environment

logger = logging.getLogger(__name__)

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
    def check_table_exists_sql_file_path(self) -> Path:
        """Path to the shared SQL that checks whether this table exists in BigQuery."""
        return SQL_PATH / "check_table_exists.sql"

    @property
    @abstractmethod
    def create_sql_file_path(self) -> Path:
        """Absolute path to the SQL file that creates this table."""

    @property
    @abstractmethod
    def check_exists_sql_file_path(self) -> Path:
        """Absolute path to the SQL file that checks for existing rows in this table."""

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

    def read_and_replace_params(self, params: dict, *, sql_file_path: Path) -> str:
        """
        Read a SQL file and substitute each ``{{ key }}`` placeholder with the
        matching value from ``params``.

        ----------
        Parameters
        ----------
        params : dict
            Mapping of placeholder names to their replacement values
            (e.g. ``{"destination": "my-project.dev_bronze.listings"}``).
        sql_file_path : Path
            SQL file to read (e.g. :attr:`create_sql_file_path` or
            :attr:`check_exists_sql_file_path`).

        ----------
        Returns
        ----------
        str
            SQL string ready to be executed against BigQuery.
        """
        sql = sql_file_path.read_text()
        for key, value in params.items():
            sql = sql.replace(f"{{{{ {key} }}}}", value)
        return sql

    def exists(self, client: bigquery.Client) -> bool:
        """
        Check whether this table exists in BigQuery.

        ----------
        Parameters
        ----------
        client : bigquery.Client
            Authenticated BigQuery client used to run the existence check.

        ----------
        Returns
        ----------
        bool
            ``True`` if the table already exists, ``False`` otherwise.
        """
        check_sql = self.read_and_replace_params(
            {
                "project": self.project,
                "dataset": self.dataset,
                "table_name": self.table,
            },
            sql_file_path=self.check_table_exists_sql_file_path,
        )
        exists = bool(next(iter(client.query(check_sql).result())).CNT > 0)
        logger.info(
            f"Table '{self.destination}' {'already exists' if exists else 'does not exist'}."
        )
        return exists

    def create(self, client: bigquery.Client) -> None:
        """
        Create this table in BigQuery using the DDL defined in :attr:`create_sql_file_path`.

        ----------
        Parameters
        ----------
        client : bigquery.Client
            Authenticated BigQuery client used to execute the DDL.
        """
        create_sql = self.read_and_replace_params(
            {"destination": self.destination},
            sql_file_path=self.create_sql_file_path,
        )
        client.query(create_sql).result()
        logger.info(f"Table '{self.destination}' created with defined schema.")
