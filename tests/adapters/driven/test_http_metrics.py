"""Tests for HTTP metrics collection."""

from src.adapters.driven.metrics.http_metrics import Metrics
from src.ports.metrics import HttpAttemptDto

__all__ = []


def test_metrics_initialization() -> None:
    """Metrics should initialize with empty window."""
    metrics = Metrics()
    assert str(metrics) == "Metrics: waiting for data …"


def test_metrics_records_attempt() -> None:
    """Metrics should record HTTP attempts."""
    metrics = Metrics(window_size=10)
    attempt = HttpAttemptDto(
        scheduled_at_sec=100.0,
        fired_at_sec=100.5,
        is_failed=False,
        status_code=200,
    )
    metrics.update(attempt)

    # Should not be empty anymore
    assert "waiting for data" not in str(metrics)
    assert "200" in str(metrics)


def test_metrics_calculates_jitter() -> None:
    """Metrics should calculate jitter correctly."""
    metrics = Metrics(window_size=10)
    attempt = HttpAttemptDto(
        scheduled_at_sec=100.0,
        fired_at_sec=100.1,  # 100ms later
        is_failed=False,
        status_code=200,
    )
    metrics.update(attempt)

    output = str(metrics)
    assert "jitter" in output.lower()
    assert "100" in output


def test_metrics_tracks_failures() -> None:
    """Metrics should track failure rate."""
    metrics = Metrics(window_size=10)

    # Add 8 successful and 2 failed attempts
    for i in range(8):
        metrics.update(HttpAttemptDto(100.0 + i, 100.0 + i, False, 200))
    for i in range(2):
        metrics.update(HttpAttemptDto(108.0 + i, 108.0 + i, True, 500))

    output = str(metrics)
    assert "fail" in output.lower()
    assert "20" in output


def test_metrics_respects_window_size() -> None:
    """Metrics should maintain sliding window of specified size."""
    metrics = Metrics(window_size=5)

    for i in range(10):
        metrics.update(HttpAttemptDto(100.0 + i, 100.0 + i, False, 200))

    output = str(metrics)
    assert "win=5/5" in output
    assert "total=10" in output


def test_metrics_tracks_total_attempts() -> None:
    """Metrics should track total attempts seen."""
    metrics = Metrics()

    for i in range(5):
        metrics.update(HttpAttemptDto(100.0 + i, 100.0 + i, False, 200))

    output = str(metrics)
    assert "total=5" in output
