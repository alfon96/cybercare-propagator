"""Settings port definition (DTO)."""

from dataclasses import dataclass
from typing import Any

__all__ = ["SettingsPort"]


@dataclass
class SettingsPort:
    """Runtime settings for the core loop.

    Decouples core from concrete configuration sources, enabling
    easy testing and implementation swapping.

    Attributes:
        period_in_sec: Seconds between event sends.
        http_post_endpoint: URL where events are sent.
        payloads: List of JSON objects to randomly select and send.
        http_health_check_endpoint: Optional URL to probe before starting.
    """

    period_in_sec: float
    http_post_endpoint: str
    payloads: list[dict[str, Any]]
    http_health_check_endpoint: str | None = None
