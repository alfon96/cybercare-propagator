"""In-memory sliding-window metrics for HTTP requests."""

from __future__ import annotations

import statistics
from collections import deque
from dataclasses import dataclass

from src.ports.metrics import HttpAttemptDto, MetricsPort

__all__ = ["Metrics"]


@dataclass(slots=True, frozen=True)
class _Sample:
    """Internal record for one HTTP attempt."""

    jitter_ms: float
    failed: bool
    status_code: int


class Metrics(MetricsPort):
    """Fast, lock-free metrics for async context.

    Tracks:
    - Average jitter (deviation from scheduled time).
    - Failure rate (HTTP errors or network failures).
    - Last status code.
    - Total attempts seen.

    Not thread-safe; create one instance per event loop.
    """

    def __init__(self, *, window_size: int = 100) -> None:
        """Initialize metrics collector.

        Args:
            window_size: Number of recent attempts to keep for statistics.
        """
        self._window: deque[_Sample] = deque(maxlen=window_size)
        self._total_seen: int = 0

    def update(self, attempt: HttpAttemptDto) -> None:
        """Record a finished HTTP attempt.

        Args:
            attempt: HTTP attempt with timing and result info.
        """
        jitter_ms = (attempt.fired_at_sec - attempt.scheduled_at_sec) * 1_000.0
        self._window.append(
            _Sample(
                jitter_ms=jitter_ms,
                failed=attempt.is_failed,
                status_code=attempt.status_code or 0,
            )
        )
        self._total_seen += 1

    def __str__(self) -> str:
        """Return human-readable one-line summary for logging.

        Returns:
            Formatted metrics string.
        """
        if not self._window:
            return "Metrics: waiting for data …"

        n_window = len(self._window)
        failures = sum(1 for s in self._window if s.failed)
        fail_pct = (failures / n_window) * 100
        avg_jitter = statistics.fmean(s.jitter_ms for s in self._window)
        last = self._window[-1]

        return (
            f"jitter={avg_jitter:5.1f} ms | "
            f"status={last.status_code:3d} | "
            f"fail={fail_pct:5.1f}% | "
            f"win={n_window}/{self._window.maxlen} | "
            f"total={self._total_seen}"
        )
