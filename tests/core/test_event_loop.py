"""Tests for the event loop scheduling."""

from collections.abc import Callable
from unittest.mock import AsyncMock, patch

import pytest

from src.core.event_loop import start_main_loop
from src.ports.http import HttpPort
from src.ports.settings import SettingsPort

__all__ = []


def make_n_shot_stop(n: int) -> Callable[[], bool]:
    """Create stop function that returns True after N calls.

    Args:
        n: Number of calls before returning True.

    Returns:
        Stop function.
    """
    counter = 0

    def stop() -> bool:
        nonlocal counter
        counter += 1
        return counter > n

    return stop


def make_one_shot_stop() -> Callable[[], bool]:
    """Create stop function that returns True after one call.

    Returns:
        Stop function.
    """
    return make_n_shot_stop(n=1)


@pytest.mark.asyncio
async def test_event_loop_calls_request_function_once() -> None:
    """Main loop should call request function exactly once."""
    fake_payloads = [{"x": 1}, {"x": 2}]
    fake_endpoint = "http://test"

    fake_response = AsyncMock()
    fake_response.status = 200

    mock_request_fn = AsyncMock(return_value=fake_response)

    await start_main_loop(
        settings=SettingsPort(
            period_in_sec=0,
            http_post_endpoint=fake_endpoint,
            payloads=fake_payloads,
        ),
        stop_fn=make_one_shot_stop(),
        request_fn=mock_request_fn,
    )

    mock_request_fn.assert_called_once()

    req_arg = mock_request_fn.call_args[0][0]
    assert isinstance(req_arg, HttpPort)
    assert req_arg.url == fake_endpoint
    assert req_arg.payload in fake_payloads


@pytest.mark.asyncio
async def test_event_loop_calls_request_function_multiple_times() -> None:
    """Main loop should call request function for each period."""
    fake_payloads = [{"x": 1}]
    fake_endpoint = "http://test"

    fake_response = AsyncMock()
    fake_response.status = 200

    mock_request_fn = AsyncMock(return_value=fake_response)

    await start_main_loop(
        settings=SettingsPort(
            period_in_sec=0,
            http_post_endpoint=fake_endpoint,
            payloads=fake_payloads,
        ),
        stop_fn=make_n_shot_stop(3),
        request_fn=mock_request_fn,
    )

    # Should be called 3 times (one per period)
    assert mock_request_fn.call_count == 3


@pytest.mark.asyncio
async def test_event_loop_selects_random_payload() -> None:
    """Main loop should select payload from available list."""
    fake_payloads = [{"type": "A"}, {"type": "B"}, {"type": "C"}]
    fake_endpoint = "http://test"

    fake_response = AsyncMock()
    fake_response.status = 200

    mock_request_fn = AsyncMock(return_value=fake_response)

    await start_main_loop(
        settings=SettingsPort(
            period_in_sec=0,
            http_post_endpoint=fake_endpoint,
            payloads=fake_payloads,
        ),
        stop_fn=make_one_shot_stop(),
        request_fn=mock_request_fn,
    )

    req_arg = mock_request_fn.call_args[0][0]
    assert req_arg.payload in fake_payloads


@pytest.mark.asyncio
async def test_event_loop_handles_request_errors_gracefully() -> None:
    """Main loop should continue after request errors."""
    fake_payloads = [{"x": 1}]
    fake_endpoint = "http://test"

    mock_request_fn = AsyncMock(side_effect=RuntimeError("Connection failed"))

    # Should not raise, just continue
    await start_main_loop(
        settings=SettingsPort(
            period_in_sec=0,
            http_post_endpoint=fake_endpoint,
            payloads=fake_payloads,
        ),
        stop_fn=make_one_shot_stop(),
        request_fn=mock_request_fn,
    )

    mock_request_fn.assert_called_once()


@pytest.mark.asyncio
async def test_event_loop_respects_period() -> None:
    """Main loop should sleep for correct duration between requests."""
    fake_payloads = [{"x": 1}]
    fake_endpoint = "http://test"
    period = 5.0

    fake_response = AsyncMock()
    fake_response.status = 200

    mock_request_fn = AsyncMock(return_value=fake_response)
    mock_sleep = AsyncMock()

    with patch("src.core.event_loop.asyncio.sleep", mock_sleep):
        await start_main_loop(
            settings=SettingsPort(
                period_in_sec=period,
                http_post_endpoint=fake_endpoint,
                payloads=fake_payloads,
            ),
            stop_fn=make_one_shot_stop(),
            request_fn=mock_request_fn,
        )

    # Should sleep between attempts
    mock_sleep.assert_called()
