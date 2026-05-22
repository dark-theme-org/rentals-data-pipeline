"""Package-level settings for BigQuery — shared audit metadata and SQL path."""

from dataclasses import dataclass
from pathlib import Path

SQL_PATH: Path = Path(__file__).parent / "sql"


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
