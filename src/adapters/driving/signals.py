"""Signal handling for graceful shutdown."""

import asyncio
import signal
from collections.abc import Callable

__all__ = ["make_stop_on_sigterm"]


def make_stop_on_sigterm() -> Callable[[], bool]:
    """Create SIGTERM-based stop flag for event loop.

    Registers SIGTERM handler that sets an asyncio.Event, returning
    an is_set-style callable for the main loop to poll.

    On Docker/Kubernetes, SIGTERM is sent 30s before SIGKILL,
    allowing graceful shutdown.

    Returns:
        Callable that returns True when SIGTERM has been received.
    """
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()

    def handle_signal() -> None:
        """Signal handler that sets the stop event on SIGTERM/SIGINT."""
        logger = __import__("logging").getLogger(__name__)
        logger.info("Termination signal received, initiating graceful shutdown...")
        stop.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_signal)

    return stop.is_set
