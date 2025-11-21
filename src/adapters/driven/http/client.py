"""HTTP client adapter with retry and metrics integration."""

import asyncio
import logging
from types import TracebackType

import aiohttp
from aiohttp import ClientResponse, ClientTimeout

from src.adapters.driven.http.retry import retry
from src.ports.http import HttpPort
from src.ports.metrics import HttpAttemptDto, MetricsPort

__all__ = ["HttpClient"]

logger = logging.getLogger(__name__)

# Configurable retry settings
PROBE_RETRIES = 5
PROBE_TIMEOUT = 10
REQUEST_RETRIES = 3
FIRST_FAILING_HTTP_CODE = 400


class HttpClient:
    """HTTP client with automatic retry and metrics collection.

    Features:
    - Retry with exponential backoff on transient errors.
    - Metrics collection (jitter, failure rate).
    - Context manager for proper resource cleanup.
    - Health check/probe functionality.
    """

    def __init__(self, metrics: MetricsPort | None = None) -> None:
        """Initialize HTTP client.

        Args:
            metrics: Optional metrics collector to track attempts.
        """
        self.metrics = metrics
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "HttpClient":
        """Enter async context manager (start session).

        Returns:
            Self for use in async with statement.
        """
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Exit async context manager (close session).

        Args:
            exc_type: Exception type if raised in context.
            exc: Exception instance if raised in context.
            tb: Traceback if raised in context.
        """
        if self.session:
            await self.session.close()

    @retry(times=PROBE_RETRIES)
    async def _probe_once(self, url: str, timeout: int = PROBE_TIMEOUT) -> ClientResponse:
        """Single HTTP GET request for health check (with retry).

        Args:
            url: URL to probe.
            timeout: Timeout in seconds.

        Returns:
            HTTP response.

        Raises:
            RuntimeError: If session not initialized.
            aiohttp exceptions: Network/timeout errors (retried by decorator).
        """
        if self.session is None:
            raise RuntimeError("Session not initialized; use 'async with' context manager")
        client_timeout = ClientTimeout(timeout)
        return await self.session.get(url, timeout=client_timeout, allow_redirects=True)

    async def probe(self, url: str, timeout: int = PROBE_TIMEOUT) -> bool:
        """Check if HTTP endpoint is reachable.

        Attempts up to PROBE_RETRIES times with exponential backoff.

        Args:
            url: URL to probe.
            timeout: Timeout in seconds.

        Returns:
            True if reachable ( 200 <= status < 300), False otherwise.
        """
        logger.info(f"Probing endpoint {url}...")
        try:
            resp = await self._probe_once(url, timeout)
            is_healthy = 200 <= resp.status < 300
            logger.info(f"Probe for {url} returned status {resp.status}")
            return is_healthy
        except Exception as e:
            logger.warning(f"Probe failed for {url}: {e}")
            return False

    @retry(times=REQUEST_RETRIES)
    async def _raw_request(self, req: HttpPort) -> ClientResponse:
        """Single HTTP POST request (with retry via decorator).

        Args:
            req: HTTP request object with URL and payload.

        Returns:
            HTTP response.

        Raises:
            RuntimeError: If session not initialized.
            aiohttp exceptions: Network/timeout errors (retried by decorator).
        """
        if self.session is None:
            raise RuntimeError("Session not initialized; use 'async with' context manager")

        return await self.session.post(req.url, json=req.payload)

    async def request(self, req: HttpPort) -> ClientResponse:
        """Send HTTP request and record metrics.

        Measures jitter (deviation from scheduled time) and records
        success/failure for statistics.

        Args:
            req: HTTP request object.

        Returns:
            HTTP response.
        """
        loop = asyncio.get_running_loop()
        scheduled = req.ideal_time_sec
        fired = loop.time()

        resp = await self._raw_request(req=req)

        if self.metrics:
            self.metrics.update(
                HttpAttemptDto(
                    scheduled_at_sec=scheduled,
                    fired_at_sec=fired,
                    is_failed=resp.status >= FIRST_FAILING_HTTP_CODE,
                    status_code=resp.status,
                )
            )
            logger.info(f"HTTP metrics: {self.metrics}")

        return resp
