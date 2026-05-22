"""Tests for BigQuery package-level settings — AuditMetadata and SQL_PATH."""

import pytest

from app.data.bigquery import AuditMetadata
from app.data.bigquery.settings import SQL_PATH


def test_audit_metadata_construction(audit_metadata: AuditMetadata) -> None:
    """Test AuditMetadata stores version, insert, and update timestamps."""
    assert audit_metadata.version_id == "test"
    assert audit_metadata.ins_ts == "2026-01-01T00:00:00Z"
    assert audit_metadata.upd_ts == "2026-01-01T00:00:00Z"


def test_audit_metadata_is_immutable(audit_metadata: AuditMetadata) -> None:
    """Test AuditMetadata raises FrozenInstanceError on field reassignment."""
    with pytest.raises(Exception):
        audit_metadata.version_id = "changed"  # type: ignore[misc]


def test_sql_path_points_to_existing_directory() -> None:
    """Test SQL_PATH resolves to an existing directory on disk."""
    assert SQL_PATH.is_dir()
