"""Observability and monitoring configuration.

This module provides functionality for:
- Configuring Logfire for application monitoring
- Loading URLs with instrumentation and logging
"""

import logging
from typing import Final

import logfire

from bot.settings import settings

logger = logging.getLogger(__name__)

FORMAT_STR: Final[str] = "%(asctime)s | %(levelname)s | %(name)s:%(lineno)d - %(message)s"


def logfire_is_enabled() -> bool:
    return bool(settings.logfire_token)


def configure_logging() -> None:
    if logfire_is_enabled():
        configure_logfire()
    else:
        logging.basicConfig(format=FORMAT_STR, level=logging.INFO)
        logger.info("Logfire is not enabled.")


def configure_logfire() -> None:
    if not logfire_is_enabled():
        logger.info("LOGFIRE_TOKEN not set, skipping Logfire configuration")
        return

    logfire.configure(token=settings.logfire_token)
    logfire.instrument_openai_agents()
    # Note: httpx and requests instrumentation disabled to reduce noise
    # logfire.instrument_httpx()
    # logfire.instrument_requests()
    logfire.instrument_redis()
    logging.basicConfig(
        format=FORMAT_STR,
        level=logging.INFO,
        handlers=[logfire.LogfireLoggingHandler()],
    )
    logger.info("Logfire configured successfully 🚀")
