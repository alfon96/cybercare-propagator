"""Metrics port definition (interface and DTO)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

__all__ = ["HttpAttemptDto", "MetricsPort"]


@dataclass(slots=True, frozen=True)
class HttpAttemptDto:
    """Immutable snapshot of a single HTTP attempt.

    Attributes:
        scheduled_at_sec: Epoch seconds when attempt was queued.
        fired_at_sec: Epoch seconds when request left the process.
        is_failed: True if considered failed (network error, 5xx, etc.).
        status_code: HTTP status code when response arrived; None otherwise.
    """

    scheduled_at_sec: float
    fired_at_sec: float
    is_failed: bool = False
    status_code: int | None = None


class MetricsPort(Protocol):
    """Interface for recording HTTP attempt metrics.

    Implementations must be async-safe and non-blocking.
    Core calls update() after each attempt; presentation layers call
    __str__() to render summaries.
    """

    def update(self, attempt: HttpAttemptDto, /) -> None:
        """Record a finished HTTP attempt.

        Args:
            attempt: The attempt to record.
        """
        ...

    def __str__(self) -> str:
        """Return concise textual summary for humans.

        Returns:
            Formatted metrics string.
        """
        ...
