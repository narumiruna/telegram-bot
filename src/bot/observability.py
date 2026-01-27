"""Observability and monitoring configuration.

This module provides functionality for:
- Configuring Logfire for application monitoring
- Configuring Langfuse for LLM observability
- Loading URLs with instrumentation and logging
"""

import base64
import os

import logfire
import nest_asyncio
from loguru import logger

from bot.env import langfuse_host
from bot.env import langfuse_is_enabled
from bot.env import langfuse_public_key
from bot.env import langfuse_secret_key
from bot.env import logfire_token


def logfire_is_enabled() -> bool:
    return bool(logfire_token)


def configure_logging() -> None:
    if logfire_is_enabled():
        configure_logfire()
    else:
        logger.info("Logfire is not enabled.")


def configure_logfire() -> None:
    logfire.configure(token=logfire_token)
    logfire.instrument_openai_agents()
    # Note: httpx and requests instrumentation disabled to reduce noise
    # logfire.instrument_httpx()
    # logfire.instrument_requests()
    logfire.instrument_redis()
    logger.configure(handlers=[logfire.loguru_handler()])


def configure_langfuse(service_name: str | None = None) -> None:
    """Configure OpenTelemetry with Langfuse authentication.

    https://langfuse.com/docs/integrations/openaiagentssdk/openai-agents
    """
    if not langfuse_is_enabled():
        return

    logger.info("Configuring OpenTelemetry with Langfuse...")

    # Build Basic Auth header.
    langfuse_auth = base64.b64encode(f"{langfuse_public_key}:{langfuse_secret_key}".encode()).decode()

    # Configure OpenTelemetry endpoint & headers
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = str(langfuse_host) + "/api/public/otel"
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {langfuse_auth}"

    logger.info("Applying nest_asyncio...")
    nest_asyncio.apply()

    logger.info("Configuring Logfire...")
    logfire.configure(
        service_name=service_name,
        send_to_logfire=False,
    )
    logfire.instrument_openai_agents()

    logger.configure(handlers=[logfire.loguru_handler()])
