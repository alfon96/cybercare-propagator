"""Tests for configuration loading and validation."""

import json
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from src.adapters.driven.config.settings import Settings, load_settings

__all__ = []

Payload = dict[str, int]


@pytest.fixture
def temp_payload_file() -> Iterator[tuple[str, list[Payload]]]:
    """Create temporary JSON payload file for testing.

    Yields:
        Tuple of (filepath, payloads).
    """
    payloads = [
        {"event_type": "message", "event_payload": "hello"},
        {"event_type": "user_joined", "event_payload": "Alice"},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(payloads, f)
        filepath = f.name
    yield filepath, payloads
    Path(filepath).unlink()


def test_settings_loads_payloads_from_file(temp_payload_file) -> None:
    """Settings should load payloads from JSON file."""
    filepath, expected_payloads = temp_payload_file

    settings = Settings(
        period_in_sec=1,
        http_post_endpoint="http://localhost:8000/event",
        payload_file_path=filepath,
    )
    settings.load_payloads()

    assert settings.payloads == expected_payloads


def test_settings_rejects_missing_payload_file() -> None:
    """Settings should reject non-existent payload file."""
    settings = Settings(
        period_in_sec=1,
        http_post_endpoint="http://localhost:8000/event",
        payload_file_path="/nonexistent/file.json",
    )

    with pytest.raises(ValueError, match="not found"):
        settings.load_payloads()


def test_settings_rejects_invalid_json_file() -> None:
    """Settings should reject invalid JSON in payload file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{ invalid json }")
        filepath = f.name

    try:
        settings = Settings(
            period_in_sec=1,
            http_post_endpoint="http://localhost:8000/event",
            payload_file_path=filepath,
        )
        with pytest.raises(ValueError, match="invalid JSON"):
            settings.load_payloads()
    finally:
        Path(filepath).unlink()


def test_settings_rejects_non_array_payload_file() -> None:
    """Settings should reject payload file that isn't a JSON array."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"type": "object"}, f)
        filepath = f.name

    try:
        settings = Settings(
            period_in_sec=1,
            http_post_endpoint="http://localhost:8000/event",
            payload_file_path=filepath,
        )
        with pytest.raises(ValueError, match="must be a JSON array"):
            settings.load_payloads()
    finally:
        Path(filepath).unlink()


def test_settings_rejects_empty_payload_file() -> None:
    """Settings should reject empty payload file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump([], f)
        filepath = f.name

    try:
        settings = Settings(
            period_in_sec=1,
            http_post_endpoint="http://localhost:8000/event",
            payload_file_path=filepath,
        )
        with pytest.raises(ValueError, match="empty"):
            settings.load_payloads()
    finally:
        Path(filepath).unlink()


def test_settings_load_settings_success(monkeypatch, temp_payload_file) -> None:
    """Load Settings should create Settings object when the input is valid."""
    monkeypatch.setenv("PERIOD_IN_SECONDS", "5")
    monkeypatch.setenv("HTTP_POST_ENDPOINT", "http://example.com")

    filepath, _ = temp_payload_file

    monkeypatch.setenv("PAYLOAD_FILE_PATH", filepath)

    assert isinstance(load_settings(), Settings)


def test_settings_load_settings_failure(monkeypatch, temp_payload_file) -> None:
    """Load Settings should raise exceptions when at least one input is invalid."""

    monkeypatch.setenv("PERIOD_IN_SECONDS", "-5")
    monkeypatch.setenv("HTTP_POST_ENDPOINT", "http://example.com")
    filepath, _ = temp_payload_file
    monkeypatch.setenv("PAYLOAD_FILE_PATH", filepath)

    # Invalid Period
    with pytest.raises(RuntimeError, match="PERIOD_IN_SECONDS must be a positive integer"):
        load_settings()
