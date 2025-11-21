"""Tests for HTTP client adapter."""

from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientResponse

from src.adapters.driven.http.client import HttpClient
from src.ports.http import HttpPort
from src.ports.metrics import HttpAttemptDto, MetricsPort

__all__ = []


class DummyMetrics(MetricsPort):
    """Metrics implementation for testing."""

    def __init__(self) -> None:
        self.attempts: list[HttpAttemptDto] = []

    def update(self, attempt: HttpAttemptDto) -> None:
        """Record attempt."""
        self.attempts.append(attempt)

    def __str__(self) -> str:
        """Return string representation."""
        return f"Recorded {len(self.attempts)} attempts"


@pytest.mark.asyncio
async def test_http_client_context_manager() -> None:
    """HTTP client should initialize and close session."""
    client = HttpClient()
    assert client.session is None

    async with client as c:
        assert c.session is not None
        assert c is client


@pytest.mark.asyncio
async def test_http_client_with_metrics() -> None:
    """HTTP client should update metrics after request."""
    metrics = DummyMetrics()
    client = HttpClient(metrics=metrics)
    client.session = AsyncMock()

    mock_response = AsyncMock()
    mock_response.status = 201
    client.session.post = AsyncMock(return_value=mock_response)

    req = HttpPort(ideal_time_sec=100.0, url="http://test/event", payload={"x": 1})

    with patch("src.adapters.driven.http.client.asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.time.return_value = 100.05
        resp = await client.request(req)

    assert resp.status == 201
    assert len(metrics.attempts) == 1
    assert metrics.attempts[0].status_code == 201
    assert metrics.attempts[0].is_failed is False


@pytest.mark.asyncio
async def test_http_client_without_metrics() -> None:
    """HTTP client should work without metrics."""
    client = HttpClient(metrics=None)
    client.session = AsyncMock()

    mock_response = AsyncMock(spec=ClientResponse)
    mock_response.status = 201
    client.session.post = AsyncMock(return_value=mock_response)

    req = HttpPort(ideal_time_sec=100.0, url="http://test/event", payload={"x": 1})

    with patch("src.adapters.driven.http.client.asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.time.return_value = 100.05
        resp = await client.request(req)

    assert resp.status == 201


@pytest.mark.asyncio
async def test_http_client_marks_failures() -> None:
    """HTTP client should mark status >= 400 as failed."""
    metrics = DummyMetrics()
    client = HttpClient(metrics=metrics)
    client.session = AsyncMock()

    mock_response = AsyncMock(spec=ClientResponse)
    mock_response.status = 500
    client.session.post = AsyncMock(return_value=mock_response)

    req = HttpPort(ideal_time_sec=100.0, url="http://test/event", payload={"x": 1})

    with patch("src.adapters.driven.http.client.asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.time.return_value = 100.05
        resp = await client.request(req)

    assert resp.status == 500
    assert metrics.attempts[0].is_failed is True
