"""Tests for main application entrypoint."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.adapters.driven.http.client import HttpClient
from src.main import main, optional_endpoint_health_check
from src.ports.settings import SettingsPort

__all__ = []


@pytest.mark.asyncio
async def test_optional_endpoint_health_check_when_disabled() -> None:
    """Health check should return True when endpoint not configured."""
    settings = SettingsPort(
        period_in_sec=1,
        http_post_endpoint="http://localhost:8000/event",
        payloads=[{"test": "payload"}],
        http_health_check_endpoint=None,  # Disabled
    )
    http_client = HttpClient()

    result = await optional_endpoint_health_check(settings, http_client)

    assert result is True


@pytest.mark.asyncio
async def test_optional_endpoint_health_check_succeeds() -> None:
    """Health check should return True when probe succeeds."""
    settings = SettingsPort(
        period_in_sec=1,
        http_post_endpoint="http://localhost:8000/event",
        payloads=[{"test": "payload"}],
        http_health_check_endpoint="http://localhost:8000/health",
    )
    http_client = HttpClient()

    with patch.object(http_client, "probe", new_callable=AsyncMock) as mock_probe:
        mock_probe.return_value = True
        result = await optional_endpoint_health_check(settings, http_client)

    assert result is True
    mock_probe.assert_called_once_with(url="http://localhost:8000/health")


@pytest.mark.asyncio
async def test_optional_endpoint_health_check_fails() -> None:
    """Health check should return False when probe fails."""
    settings = SettingsPort(
        period_in_sec=1,
        http_post_endpoint="http://localhost:8000/event",
        payloads=[{"test": "payload"}],
        http_health_check_endpoint="http://localhost:8000/health",
    )
    http_client = HttpClient()

    with patch.object(http_client, "probe", new_callable=AsyncMock) as mock_probe:
        mock_probe.return_value = False
        result = await optional_endpoint_health_check(settings, http_client)

    assert result is False


@pytest.mark.asyncio
async def test_main_starts_and_runs_successfully() -> None:
    """Main should start propagator and handle normal flow."""
    with (
        patch("src.main.configure_logs"),
        patch("src.main.load_settings") as mock_load_settings,
        patch("src.main.HttpClient") as mock_http_client_class,
        patch("src.main.Metrics"),
        patch("src.main.make_stop_on_sigterm"),
        patch("src.main.start_main_loop", new_callable=AsyncMock),
        patch("src.main.optional_endpoint_health_check", new_callable=AsyncMock) as mock_health,
    ):
        # Setup mocks
        mock_config = Mock()
        mock_config.period_in_sec = 5
        mock_config.http_post_endpoint = "http://localhost:8000/event"
        mock_config.http_health_endpoint = None
        mock_config.payloads = [{"test": "payload"}]
        mock_load_settings.return_value = mock_config

        mock_http_client = AsyncMock()
        mock_http_client_class.return_value = mock_http_client
        mock_http_client.__aenter__.return_value = mock_http_client

        mock_health.return_value = True

        # Run main
        await main()

        # Verify calls
        mock_load_settings.assert_called_once()
        mock_health.assert_called_once()


@pytest.mark.asyncio
async def test_main_aborts_on_health_check_failure() -> None:
    """Main should abort startup if health check fails."""
    with (
        patch("src.main.configure_logs"),
        patch("src.main.load_settings") as mock_load_settings,
        patch("src.main.HttpClient") as mock_http_client_class,
        patch("src.main.Metrics"),
        patch("src.main.make_stop_on_sigterm"),
        patch("src.main.start_main_loop", new_callable=AsyncMock) as mock_loop,
        patch("src.main.optional_endpoint_health_check", new_callable=AsyncMock) as mock_health,
    ):
        # Setup mocks
        mock_config = Mock()
        mock_config.period_in_sec = 5
        mock_config.http_post_endpoint = "http://localhost:8000/event"
        mock_config.http_health_endpoint = "http://localhost:8000/health"
        mock_config.payloads = [{"test": "payload"}]
        mock_load_settings.return_value = mock_config

        mock_http_client = AsyncMock()
        mock_http_client_class.return_value = mock_http_client
        mock_http_client.__aenter__.return_value = mock_http_client

        mock_health.return_value = False  # Health check fails

        # Run main
        await main()

        # Main loop should NOT be called
        mock_loop.assert_not_called()


@pytest.mark.asyncio
async def test_main_continues_on_loop_exception() -> None:
    """Main loop should catch exceptions and continue running."""
    with (
        patch("src.main.configure_logs"),
        patch("src.main.load_settings") as mock_load_settings,
        patch("src.main.HttpClient") as mock_http_client_class,
        patch("src.main.Metrics"),
        patch("src.main.make_stop_on_sigterm"),
        patch("src.main.start_main_loop", new_callable=AsyncMock) as mock_loop,
        patch("src.main.optional_endpoint_health_check", new_callable=AsyncMock) as mock_health,
        patch("src.main.logger") as mock_logger,
    ):
        # Setup mocks
        mock_config = AsyncMock()
        mock_config.period_in_sec = 5
        mock_config.http_post_endpoint = "http://localhost:8000/event"
        mock_config.http_health_endpoint = None
        mock_config.payloads = [{"test": "payload"}]
        mock_load_settings.return_value = mock_config
        mock_http_client = AsyncMock()
        mock_http_client_class.return_value = mock_http_client
        mock_http_client.__aenter__.return_value = mock_http_client
        mock_health.return_value = True

        test_error = RuntimeError("Test error in loop")
        mock_loop.side_effect = test_error

        # Run main - should NOT raise
        try:
            await main()
        except RuntimeError:
            pytest.fail("main() should not raise; exceptions are caught internally")

        # Verify error was logged
        mock_logger.error.assert_called()
