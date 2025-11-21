"""Tests for HTTP retry decorator."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.adapters.driven.http.retry import RETRYABLE_ERRORS, retry

__all__ = []


@pytest.mark.asyncio
@pytest.mark.parametrize("exc_type", RETRYABLE_ERRORS)
async def test_retry_decorator_retries_on_transient_errors(
    exc_type: type[BaseException],
) -> None:
    """Retry decorator should retry on transient errors."""
    exc = exc_type(Mock(), Mock())
    mock_fn = AsyncMock(side_effect=exc)
    wrapped = retry(times=3)(mock_fn)

    with (
        patch("src.adapters.driven.http.retry.asyncio.sleep", new=AsyncMock()),
        pytest.raises(exc_type),
    ):
        await wrapped()

    # Should attempt 3 times
    assert mock_fn.call_count == 3


@pytest.mark.asyncio
async def test_retry_decorator_first_call_success() -> None:
    """Retry decorator should not retry on first call success."""
    fake_response = AsyncMock()
    fake_response.status = 200

    mock_fn = AsyncMock(return_value=fake_response)
    wrapped = retry(times=3)(mock_fn)

    result = await wrapped()

    # Should call only once
    assert mock_fn.call_count == 1
    assert result == fake_response


@pytest.mark.asyncio
async def test_retry_decorator_does_not_retry_permanent_errors() -> None:
    """Retry decorator should not retry non-transient errors."""
    exc = ValueError("Invalid request")  # Not in RETRYABLE_ERRORS
    mock_fn = AsyncMock(side_effect=exc)
    wrapped = retry(times=3)(mock_fn)

    with pytest.raises(ValueError):
        await wrapped()

    # Should only try once
    assert mock_fn.call_count == 1


@pytest.mark.asyncio
async def test_retry_decorator_delays_between_attempts() -> None:
    """Retry decorator should delay between retry attempts."""
    exc = RETRYABLE_ERRORS[0](Mock(), Mock())
    mock_fn = AsyncMock(side_effect=exc)
    wrapped = retry(times=3, delay_sec=(0.1, 0.2, 0.3))(mock_fn)

    mock_sleep = AsyncMock()
    with (
        patch("src.adapters.driven.http.retry.asyncio.sleep", mock_sleep),
        pytest.raises(RETRYABLE_ERRORS[0]),
    ):
        await wrapped()

    # Should sleep between attempts (2 sleeps for 3 attempts)
    assert mock_sleep.call_count == 2
