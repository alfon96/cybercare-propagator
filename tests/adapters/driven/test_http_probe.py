"""Tests for HTTP health check probing."""

from unittest.mock import AsyncMock

import pytest

from src.adapters.driven.http.client import HttpClient

__all__ = []


@pytest.mark.asyncio
async def test_probe_success() -> None:
    """probe() should return True when GET succeeds with  200 <= status < 300."""
    client = HttpClient()
    client.session = AsyncMock()

    mock_response = AsyncMock()
    mock_response.status = 200
    client.session.get = AsyncMock(return_value=mock_response)

    result = await client.probe("http://example.com")

    assert result is True
    client.session.get.assert_called_once()


@pytest.mark.asyncio
async def test_probe_failure() -> None:
    """probe() should return False for >=300 status codes."""
    client = HttpClient()
    client.session = AsyncMock()

    mock_response = AsyncMock()
    mock_response.status = 300
    client.session.get = AsyncMock(return_value=mock_response)

    result = await client.probe("http://example.com")

    assert result is False


@pytest.mark.asyncio
async def test__probe_once_raises_if_session_not_initialized() -> None:
    """_probe_once should raise if session is None."""
    client = HttpClient()
    client.session = None  # force the error path

    with pytest.raises(RuntimeError, match="Session not initialized"):
        await client._probe_once("http://example.com")


@pytest.mark.asyncio
async def test_probe_returns_false_on_exception() -> None:
    """probe() should return False when _probe_once raises."""
    client = HttpClient()
    client._probe_once = AsyncMock(side_effect=RuntimeError("boom"))

    result = await client.probe("http://example.com")

    client._probe_once.assert_awaited_once()
    assert result is False
