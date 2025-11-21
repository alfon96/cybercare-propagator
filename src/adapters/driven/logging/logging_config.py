"""Structured logging setup for the propagator."""

import logging

__all__ = ["configure_logs"]


def configure_logs() -> None:
    """Configure console logging.

    Sets up:
    - Root logger at INFO level.
    - Framework loggers (aiohttp, asyncio) at WARNING level.
    - Application loggers (src) at DEBUG level.
    - Structured format with timestamp, level, module, and line number.
    """
    log_format = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"
    date_format = "%d/%m/%y %H:%M:%S"

    formatter = logging.Formatter(log_format, date_format)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # Root logger
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    # Suppress verbose framework loggers
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Application loggers
    logging.getLogger("src").setLevel(logging.DEBUG)
