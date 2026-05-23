"""Tests for the Table abstract base class concrete methods."""

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from app.data.bigquery import BronzeListingsTable
from app.utils import CloudSettings


def test_table_invalid_env_raises() -> None:
    """Test Table.__post_init__ raises ValueError for an unknown environment."""
    with pytest.raises(ValueError, match="not a valid"):
        BronzeListingsTable(env="staging", project=CloudSettings.PROJECT_ID)


def test_table_destination(bronze_table: BronzeListingsTable) -> None:
    """Test destination formats project.dataset.table correctly."""
    assert bronze_table.destination == f"{CloudSettings.PROJECT_ID}.dev_bronze.listings"


def test_read_and_replace_params_substitutes_placeholder(
    bronze_table: BronzeListingsTable,
    tmp_path: Path,
) -> None:
    """Test read_and_replace_params replaces every {{ key }} with its value."""
    sql_file = tmp_path / "test.sql"
    sql_file.write_text("SELECT * FROM `{{ destination }}` WHERE x = '{{ val }}'")
    result = bronze_table.read_and_replace_params(
        {"destination": "p.d.t", "val": "foo"},
        sql_file_path=sql_file,
    )
    assert result == "SELECT * FROM `p.d.t` WHERE x = 'foo'"


def test_exists_returns_true_when_table_found(
    bronze_table: BronzeListingsTable,
    mocker: MockerFixture,
) -> None:
    """Test exists returns True when INFORMATION_SCHEMA reports CNT=1."""
    mock_row = mocker.MagicMock()
    mock_row.CNT = 1
    client = mocker.MagicMock()
    client.query.return_value.result.return_value = iter([mock_row])
    assert bronze_table.exists(client) is True


def test_exists_returns_false_when_table_not_found(
    bronze_table: BronzeListingsTable,
    mocker: MockerFixture,
) -> None:
    """Test exists returns False when INFORMATION_SCHEMA reports CNT=0."""
    mock_row = mocker.MagicMock()
    mock_row.CNT = 0
    client = mocker.MagicMock()
    client.query.return_value.result.return_value = iter([mock_row])
    assert bronze_table.exists(client) is False


def test_create_executes_ddl(
    bronze_table: BronzeListingsTable,
    mocker: MockerFixture,
) -> None:
    """Test create calls client.query with the fully-rendered DDL and waits for completion."""
    client = mocker.MagicMock()
    bronze_table.create(client)
    client.query.assert_called_once()
    ddl_arg = client.query.call_args[0][0]
    assert "{{ destination }}" not in ddl_arg
    assert bronze_table.destination in ddl_arg
    client.query.return_value.result.assert_called_once()
