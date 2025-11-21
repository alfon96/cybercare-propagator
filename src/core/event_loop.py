"""Main event loop that periodically sends HTTP requests."""

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

from aiohttp import ClientResponse
from aiohttp.client_exceptions import ClientConnectorError

from src.ports.http import HttpPort
from src.ports.settings import SettingsPort

__all__ = ["start_main_loop", "get_now_time"]

logger = logging.getLogger(__name__)


def get_now_time() -> float:
    """Get current monotonic time in seconds.

    Uses event loop's monotonic clock for accurate scheduling
    without wall-clock drift.

    Returns:
        Current time in seconds (monotonic).
    """
    return asyncio.get_running_loop().time()


async def start_main_loop(
    settings: SettingsPort,
    stop_fn: Callable[[], bool],
    request_fn: Callable[[HttpPort], Awaitable[ClientResponse]],
) -> None:
    """Run the main scheduling loop.

    Periodically:
    1. Select a random payload.
    2. Schedule an HTTP request as a background task (fire-and-forget).
    3. Sleep to maintain the configured period (based on monotonic time).
    4. Repeat until stop_fn() returns True, then cancel in-flight tasks.

    Args:
        settings: Runtime configuration (period, endpoint, payloads).
        stop_fn: Callable that returns True when loop should exit.
        request_fn: Async function used to send one HTTP request.

    Notes:
        - The loop never awaits individual requests: each send runs in its own
          asyncio.Task so that scheduling stays periodic even if the consumer
          is slow.
        - On shutdown (stop_fn() -> True), all pending request tasks are
          cancelled and awaited to ensure a clean exit.
    """
    next_tick: float = get_now_time()
    pending: set[asyncio.Task[None]] = set()
    loop = asyncio.get_running_loop()

    async def _run_once(req: HttpPort) -> None:
        """Run one request and handle/log errors."""
        try:
            await request_fn(req)
        except ClientConnectorError as e:
            logger.warning(f"Consumer unreachable: {e}")
        except asyncio.CancelledError:
            logger.info("Shutdown requested (task cancelled).")
        except KeyboardInterrupt:
            logger.info("Shutdown requested (keyboard interrupt).")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Unexpected error in send task: {e}", exc_info=True)
        finally:
            task = asyncio.current_task()
            if task is not None:
                pending.discard(task)

    while not stop_fn():
        randomized_payload = random.choice(settings.payloads)
        request_args = HttpPort(
            ideal_time_sec=next_tick,
            url=settings.http_post_endpoint,
            payload=randomized_payload,
        )

        # Fire and forget
        task: asyncio.Task[None] = loop.create_task(_run_once(request_args))
        pending.add(task)

        next_tick += settings.period_in_sec
        sleep_duration = max(0, next_tick - get_now_time())
        await asyncio.sleep(sleep_duration)

    if pending:
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
