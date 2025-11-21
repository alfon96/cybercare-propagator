"""Retry logic for transient HTTP errors."""

import asyncio
from collections.abc import Awaitable, Callable
from functools import wraps

import aiohttp
from aiohttp import ClientResponse

__all__ = ["retry", "RETRYABLE_ERRORS"]

# Exceptions considered transient and eligible for retry
RETRYABLE_ERRORS = (
    aiohttp.ClientConnectorError,  # Connection refused, DNS failed
    aiohttp.ClientConnectionError,  # Connection error
    aiohttp.ClientOSError,  # OS-level network error
    aiohttp.ServerTimeoutError,  # Server timeout
    aiohttp.ClientPayloadError,  # Streaming error
)

AsyncHttpFn = Callable[..., Awaitable[ClientResponse]]


def retry(
    times: int = 3,
    delay_sec: tuple[float, ...] = (0.2, 0.5, 1.0),
) -> Callable[[AsyncHttpFn], AsyncHttpFn]:
    """Decorate async HTTP function with exponential backoff retry.

    Retries on transient errors (connection, timeout) but not permanent
    errors (4xx, invalid requests).

    Args:
        times: Number of attempts (1 = no retry).
        delay_sec: Delays between attempts in seconds.

    Returns:
        Decorator function.

    Example:
        @retry(times=3, delay_sec=(0.2, 0.5, 1.0))
        async def my_http_call():
            return await session.get(url)
    """

    def decorator(func: AsyncHttpFn) -> AsyncHttpFn:
        @wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> ClientResponse:
            last_exc: BaseException | None = None

            for attempt in range(times):
                try:
                    return await func(*args, **kwargs)
                except RETRYABLE_ERRORS as e:
                    last_exc = e
                    if attempt == times - 1:
                        # Last attempt failed, log and raise
                        logger = __import__("logging").getLogger(__name__)
                        logger.debug(f"Retry exhausted after {times} attempts: {e}")
                        raise
                    # Sleep before retry with exponential backoff
                    delay_idx = min(attempt, len(delay_sec) - 1)
                    await asyncio.sleep(delay_sec[delay_idx])
                except Exception:
                    # Non-transient errors: do not retry
                    raise

            raise last_exc or RuntimeError("Retry wrapper exhausted")

        return wrapper

    return decorator
