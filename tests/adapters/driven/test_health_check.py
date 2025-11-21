"""Tests for health check validator."""
from unittest.mock import patch

from src.adapters.driven.config.health_check import main

__all__ = []


def test_health_check_success() -> None:
    """Health check should return 0 when configuration loads successfully."""
    with patch("src.adapters.driven.config.health_check.load_settings") as mock_load:
        mock_load.return_value = None
        result = main()

    assert result == 0


def test_health_check_failure_on_config_error() -> None:
    """Health check should return 1 when configuration fails to load."""
    with patch("src.adapters.driven.config.health_check.load_settings") as mock_load:
        mock_load.side_effect = RuntimeError("Invalid configuration")
        result = main()

    assert result == 1
