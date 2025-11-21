"""Healthcheck validator for container orchestration."""

import logging

from src.adapters.driven.config.settings import load_settings
from src.adapters.driven.logging.logging_config import configure_logs

__all__ = ["main"]

logger = logging.getLogger(__name__)


def main() -> int:
    """Run health check for container orchestration.

    Validates:
    - Required environment variables are set.
    - Payload file exists and is valid JSON.
    - Configuration can be loaded successfully.

    Returns:
        0 if healthy, 1 if unhealthy.
    """
    configure_logs()

    try:
        _ = load_settings()
    except Exception as exc:
        logger.error(f"Propagator healthcheck FAILED: {exc}")
        return 1

    logger.info("Propagator healthcheck OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
