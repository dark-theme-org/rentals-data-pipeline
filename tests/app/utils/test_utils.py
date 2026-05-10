"""Test enums exposed by the shared utils module."""

from app.utils.utils import Environment, FileExtensions


def test_environment_members() -> None:
    """Test Environment exposes DEV/TEST/PROD with lowercase string values."""
    assert Environment.DEV == "dev"
    assert Environment.TEST == "test"
    assert Environment.PROD == "prod"


def test_file_extensions_members() -> None:
    """Test FileExtensions exposes JSON with lowercase value."""
    assert FileExtensions.JSON == "json"
