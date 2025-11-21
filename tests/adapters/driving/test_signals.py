"""Tests for SIGTERM signal handling."""

import asyncio
import os
import signal

import pytest

from src.adapters.driving.signals import make_stop_on_sigterm

__all__ = []


@pytest.mark.asyncio
async def test_stop_function_returns_true_after_sigterm() -> None:
    """Stop function should return True after SIGTERM is sent."""
    stop_fn = make_stop_on_sigterm()

    # Initial state
    assert stop_fn() is False

    # Send SIGTERM to current process
    os.kill(os.getpid(), signal.SIGTERM)

    # Give event loop time to process signal
    await asyncio.sleep(0.1)

    # Should now return True
    assert stop_fn() is True
