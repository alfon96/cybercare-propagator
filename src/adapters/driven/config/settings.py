"""Configuration loading from environment variables and files."""

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field, HttpUrl, TypeAdapter, field_validator

__all__ = ["Settings", "load_settings"]

load_dotenv()

logger = logging.getLogger(__name__)
_http_url_adapter = TypeAdapter(HttpUrl)


class Settings(BaseModel):
    """Runtime configuration for the propagator service.

    Attributes:
        period_in_sec: Interval between events in seconds (must be positive).
        http_post_endpoint: HTTP endpoint that will receive events.
        http_health_endpoint: Optional endpoint to probe before starting.
        payload_file_path: Path to JSON file with event payloads.
        payloads: List of event payload objects (loaded from file).
    """

    period_in_sec: int = Field(..., gt=0, description="Interval between events in seconds.")
    http_post_endpoint: str = Field(..., description="HTTP endpoint that will receive events.")
    http_health_endpoint: str | None = Field(
        default=None,
        description=(
            "Optional HTTP endpoint to probe for health. "
            "If not set, no health check is performed."
        ),
    )
    payload_file_path: str = Field(..., description="Path to JSON file containing event payloads")
    payloads: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of event payloads (populated from file).",
    )

    @field_validator("http_post_endpoint")
    @classmethod
    def validate_http_post_endpoint(cls, v: str) -> str:
        """Validate that endpoint is a valid HTTP(S) URL.

        Args:
            v: Endpoint URL to validate.

        Returns:
            The validated URL.

        Raises:
            ValueError: If URL is invalid or not http.
        """
        try:
            url = _http_url_adapter.validate_python(v)
            if url.scheme not in ("http"):
                raise ValueError("Only http:// endpoints allowed")
        except Exception as e:
            raise ValueError(f"Invalid HTTP endpoint: {e}") from e
        return v

    @field_validator("http_health_endpoint")
    @classmethod
    def validate_http_health_endpoint(cls, v: str | None) -> str | None:
        """Validate that health endpoint (if provided) is a valid HTTP(S) URL.

        Args:
            v: Health endpoint URL to validate (can be None).

        Returns:
            The validated URL or None.

        Raises:
            ValueError: If URL is invalid or not http.
        """
        if v is None:
            return v
        try:
            url = _http_url_adapter.validate_python(v)
            if url.scheme not in ("http"):
                raise ValueError("Only http:// endpoints allowed")
        except Exception as e:
            raise ValueError(f"Invalid health endpoint: {e}") from e
        return v

    def load_payloads(self) -> None:
        """Load and validate payloads from JSON file.

        Raises:
            ValueError: If file not found, invalid JSON, wrong format, or empty.
        """
        try:
            with open(self.payload_file_path) as f:
                data = json.load(f)
        except FileNotFoundError as e:
            raise ValueError(f"Payload file not found: {self.payload_file_path}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Payload file contains invalid JSON: {self.payload_file_path}") from e

        if not isinstance(data, list):
            raise ValueError("Payload file must be a JSON array")
        if not data:
            raise ValueError("Payload file is empty")
        if not all(isinstance(x, dict) for x in data):
            raise ValueError("Each payload must be a JSON object")

        self.payloads = data
        logger.debug(f"Loaded {len(data)} payloads from {self.payload_file_path}")


def load_settings() -> Settings:
    """Load and validate settings from environment and files.

    Required environment variables:
    - PERIOD_IN_SECONDS: Positive integer for event interval.
    - HTTP_POST_ENDPOINT: Valid HTTP(S) URL for consumer.
    - PAYLOAD_FILE_PATH: Path to JSON file with event payloads.

    Optional:
    - HEALTH_CHECK_ENDPOINT: URL to probe before starting.

    Returns:
        Validated Settings object.

    Raises:
        RuntimeError: If required env vars missing or invalid.
        ValueError: If configuration is invalid.
    """
    try:
        period_raw = os.environ["PERIOD_IN_SECONDS"]
        http_endpoint = os.environ["HTTP_POST_ENDPOINT"]
        payload_path = os.environ["PAYLOAD_FILE_PATH"]
    except KeyError as e:
        raise RuntimeError(f"Missing required environment variable: {e.args[0]}") from e

    health_check_endpoint = os.getenv("HEALTH_CHECK_ENDPOINT")

    try:
        period_in_sec = int(period_raw)
        if period_in_sec <= 0:
            raise ValueError("Must be positive")
    except ValueError as e:
        raise RuntimeError(
            f"PERIOD_IN_SECONDS must be a positive integer (got: {period_raw})"
        ) from e

    settings = Settings(
        period_in_sec=period_in_sec,
        http_post_endpoint=http_endpoint,
        http_health_endpoint=health_check_endpoint,
        payload_file_path=payload_path,
    )

    # Load and validate payload file
    settings.load_payloads()

    logger.info(
        f"Propagator configured: period={settings.period_in_sec}s, "
        f"endpoint={settings.http_post_endpoint}, "
        f"payloads={len(settings.payloads)}, "
        f"health_check={settings.http_health_endpoint or '<disabled>'}"
    )

    return settings
