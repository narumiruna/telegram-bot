"""Observability and monitoring configuration.

This module provides functionality for:
- Configuring Logfire for application monitoring
- Loading URLs with instrumentation and logging
"""

import logfire
from loguru import logger

from bot.settings import settings


def logfire_is_enabled() -> bool:
    return bool(settings.logfire_token)


def configure_logging() -> None:
    if logfire_is_enabled():
        configure_logfire()
    else:
        logger.info("Logfire is not enabled.")


def configure_logfire() -> None:
    logfire.configure(token=settings.logfire_token)
    logfire.instrument_openai_agents()
    # Note: httpx and requests instrumentation disabled to reduce noise
    # logfire.instrument_httpx()
    # logfire.instrument_requests()
    logfire.instrument_redis()
    logger.configure(handlers=[logfire.loguru_handler()])
