"""Table descriptors for BigQuery-backed storage targets."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from google.cloud import bigquery

from app.utils import Environment

logger = logging.getLogger(__name__)

BRONZE_DATASET: str = "{env}_bronze"
DESTINATION_PATH: str = "{project}.{dataset}.{table}"


@dataclass(frozen=True, kw_only=True)
class AuditMetadata:
    """
    Warehouse-audit metadata set by the load job.

    Fields mirror the ``AUD_*`` columns in the Bronze schema:
    ``AUD_VERSION_ID``, ``AUD_INS_TS``, ``AUD_UPD_TS``.
    """

    version_id: str
    ins_ts: str
    upd_ts: str


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
        return Path(__file__).parent / "sql" / "check_table_exists.sql"

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


@dataclass(frozen=True, kw_only=True)
class BronzeListingsTable(Table):
    """:class:`Table` for the Bronze layer of scraped real-estate listings."""

    @dataclass(frozen=True, kw_only=True)
    class SourceMetadata:
        """
        Source-lineage metadata derived from the GCS blob path.

        Fields mirror the ``SRC_*`` columns in the Bronze schema and encode
        which blob, site, city, property type, page, and scraper run produced
        each row.
        """

        blob: str
        site_name: str
        city_name: str
        property_type_cat: str
        page_num: int
        executed_at_ts: str

    @property
    def dataset(self) -> str:
        """Dataset name scoped by environment (e.g. ``"dev_bronze"``, ``"prod_bronze"``)."""
        return BRONZE_DATASET.format(env=self.env)

    @property
    def table(self) -> str:
        """Fixed table name for scraped listings."""
        return "listings"

    @property
    def create_sql_file_path(self) -> Path:
        """Path to the DDL that creates ``{env}_bronze.listings``."""
        return Path(__file__).parent / "sql" / "create_bronze_listings_table.sql"

    @property
    def check_exists_sql_file_path(self) -> Path:
        """Path to the query that checks for existing rows in ``{env}_bronze.listings``."""
        return Path(__file__).parent / "sql" / "check_bronze_listings_exists.sql"

    def blob_already_loaded(
        self,
        client: bigquery.Client,
        *,
        blob_name: str,
        executed_at: str,
    ) -> bool:
        """
        Check whether a specific GCS blob has already been loaded into this table.

        ----------
        Parameters
        ----------
        client : bigquery.Client
            Authenticated BigQuery client used to run the check query.
        blob_name : str
            Full GCS blob path to look up (e.g. ``"dev/vivareal/macae/apartment/1/blob.json"``).
        executed_at : str
            Scraper run date in ``YYYY-MM-DD`` format used for partition pruning.

        ----------
        Returns
        ----------
        bool
            ``True`` if the blob is already present in the table, ``False`` otherwise.
        """
        check_sql = self.read_and_replace_params(
            {
                "destination": self.destination,
                "executed_at": executed_at,
                "blob_name": blob_name,
            },
            sql_file_path=self.check_exists_sql_file_path,
        )
        loaded = bool(next(iter(client.query(check_sql).result()), None) is not None)
        logger.info(
            f"Blob '{blob_name}' {'already loaded' if loaded else 'not yet loaded'} "
            f"into '{self.destination}'."
        )
        return loaded

    @property
    def load_job_config(self) -> bigquery.LoadJobConfig:
        """BigQuery load job config for append-only writes to this table."""
        return bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_APPEND)

    def row_schema(self, listing: dict, *, src: SourceMetadata, aud: AuditMetadata) -> dict:
        """
        Map a single raw scraped listing to a Bronze table row dict.

        ----------
        Parameters
        ----------
        listing : dict
            Raw listing object from the scraped JSON (schema.org structure).
        src : SourceMetadata
            Source-lineage metadata derived from the GCS blob.
        aud : AuditMetadata
            Warehouse-audit metadata set at load time.

        ----------
        Returns
        ----------
        dict
            Column-name → value mapping ready for ``load_table_from_json``.
        """
        address = listing.get("address", {})
        floor_size = listing.get("floorSize", {})
        offers = listing.get("offers", {})
        potential_action = offers.get("potentialAction", {})
        price_spec = potential_action.get("priceSpecification", {})
        property_value = offers.get("propertyValue", {})

        return {
            "LISTING_ID": listing.get("@id"),
            "LISTING_NAME": listing.get("name"),
            "LISTING_URL": listing.get("url"),
            "LISTING_DESCRIPTION": listing.get("description"),
            "LISTING_PETS_ALLOWED_FLAG": listing.get("petsAllowed"),
            "LISTING_NUMBER_OF_ROOMS_AMT": listing.get("numberOfRooms"),
            "LISTING_NUMBER_OF_BEDROOMS_AMT": listing.get("numberOfBedrooms"),
            "LISTING_NUMBER_OF_BATHROOMS_AMT": listing.get("numberOfBathroomsTotal"),
            "LISTING_ADDRESS_INFOS": (
                {
                    "STREET_ADDRESS": address.get("streetAddress"),
                    "LOCALITY": address.get("addressLocality"),
                    "REGION": address.get("addressRegion"),
                    "COUNTRY": address.get("addressCountry"),
                }
                if address
                else None
            ),
            "LISTING_FLOOR_SIZE_INFOS": (
                {
                    "VALUE": floor_size.get("value"),
                    "UNIT_CODE": floor_size.get("unitCode"),
                }
                if floor_size
                else None
            ),
            "LISTING_IMAGES_LIST": listing.get("image") or [],
            "LISTING_AMENITY_FEATURES_INFOS": [
                {"NAME": f.get("name"), "VALUE": f.get("value")}
                for f in (listing.get("amenityFeature") or [])
            ],
            "LISTING_OFFERS_INFOS": (
                {
                    "PRICE": offers.get("price"),
                    "PRICE_CURRENCY": offers.get("priceCurrency"),
                    "AVAILABILITY": offers.get("availability"),
                    "POTENTIAL_ACTION": (
                        {
                            "TARGET": potential_action.get("target"),
                            "PRICE_SPECIFICATION": (
                                {
                                    "PRICE": price_spec.get("price"),
                                    "PRICE_CURRENCY": price_spec.get("priceCurrency"),
                                }
                                if price_spec
                                else None
                            ),
                        }
                        if potential_action
                        else None
                    ),
                    "PROPERTY_VALUE": (
                        {
                            "NAME": property_value.get("name"),
                            "VALUE": property_value.get("value"),
                            "UNIT_TEXT": property_value.get("unitText"),
                        }
                        if property_value
                        else None
                    ),
                }
                if offers
                else None
            ),
            "SRC_BLOB": src.blob,
            "SRC_SITE_NAME": src.site_name,
            "SRC_CITY_NAME": src.city_name,
            "SRC_PROPERTY_TYPE_CAT": src.property_type_cat,
            "SRC_PAGE_NUM": src.page_num,
            "SRC_EXECUTED_AT_TS": src.executed_at_ts,
            "AUD_VERSION_ID": aud.version_id,
            "AUD_INS_TS": aud.ins_ts,
            "AUD_UPD_TS": aud.upd_ts,
        }
