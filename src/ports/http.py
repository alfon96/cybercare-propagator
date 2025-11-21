"""HTTP port definition (DTO)."""

from dataclasses import dataclass
from typing import Any

__all__ = ["HttpPort"]


@dataclass
class HttpPort:
    """HTTP request to be sent by propagator.

    Decouples core scheduling logic from HTTP implementation details.

    Attributes:
        ideal_time_sec: Monotonic time when request should have been sent.
        url: Target HTTP endpoint URL.
        payload: JSON-serializable dictionary to send as request body.
    """

    ideal_time_sec: float
    url: str
    payload: dict[str, Any]
