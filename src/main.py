"""Application entrypoint."""

import asyncio
import logging

from src.adapters.driven.config.settings import load_settings
from src.adapters.driven.http.client import HttpClient
from src.adapters.driven.logging.logging_config import configure_logs
from src.adapters.driven.metrics.http_metrics import Metrics
from src.adapters.driving.signals import make_stop_on_sigterm
from src.core.event_loop import start_main_loop
from src.ports.settings import SettingsPort

__all__ = ["main"]

logger = logging.getLogger(__name__)


async def main() -> None:
    """Start the Event Propagator service.

    Startup sequence:
    1. Configure logging.
    2. Load and validate configuration.
    3. Optionally probe consumer health.
    4. Run the main propagation loop.
    5. Gracefully shutdown on SIGTERM.
    """
    configure_logs()
    logger.info("Starting Event Propagator service...")

    try:
        config = load_settings()
    except (RuntimeError, ValueError) as exc:
        logger.error(
            "Configuration error: %s\n"
            "Hint: check PERIOD_IN_SECONDS, HTTP_POST_ENDPOINT, "
            "PAYLOAD_FILE_PATH and that the payload file exists and is valid JSON.",
            exc,
        )
        return

    # Wrap config into port so core depends on interface (hexagonal)
    settings_port = SettingsPort(
        period_in_sec=config.period_in_sec,
        http_post_endpoint=config.http_post_endpoint,
        payloads=config.payloads,
        http_health_check_endpoint=config.http_health_endpoint,
    )

    metrics = Metrics()
    http_client = HttpClient(metrics=metrics)

    async with http_client as http:
        if not await optional_endpoint_health_check(settings_port, http):
            return

        try:
            await start_main_loop(
                settings=settings_port,
                stop_fn=make_stop_on_sigterm(),
                request_fn=http.request,
            )
        except Exception as e:
            logger.error(f"Unhandled exception in main loop: {e}", exc_info=True)

        logger.info("Event propagator stopped.")


async def optional_endpoint_health_check(settings_port: SettingsPort, http: HttpClient) -> bool:
    """Perform optional health check before starting propagation.

    Only runs if HEALTH_CHECK_ENDPOINT is configured.

    Args:
        settings_port: Runtime settings.
        http: HTTP client for probing.

    Returns:
        True if healthy or check disabled, False if check failed.
    """
    if settings_port.http_health_check_endpoint:
        logger.info(f"Performing health check on {settings_port.http_health_check_endpoint}...")
        if not await http.probe(url=settings_port.http_health_check_endpoint):
            logger.error(
                f"Health check failed for {settings_port.http_health_check_endpoint}, "
                "aborting startup"
            )
            return False

        logger.info("Health check passed, starting propagation...")
    return True


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        import logging

        logging.getLogger(__name__).info("Shutdown requested by user (Ctrl+C).")
