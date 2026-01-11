import asyncio
import base64
import functools
import json
import os
import re
from pathlib import Path
from typing import Any

import kabigon
import logfire
import nest_asyncio
import telegraph
from loguru import logger


def save_text(text: str, f: str) -> None:
    with open(f, "w") as fp:
        fp.write(text)


def load_json(f: str | Path) -> Any:
    path = Path(f)
    if path.suffix != ".json":
        raise ValueError(f"File {f} is not a json file")

    with path.open(encoding="utf-8") as fp:
        return json.load(fp)


def save_json(data: Any, f: str) -> None:
    with Path(f).open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=4)


def parse_url(s: str) -> str:
    url_pattern = r"https?://[^\s]+"

    match = re.search(url_pattern, s)
    if match:
        return match.group(0)

    return ""


@functools.cache
def get_telegraph_client() -> telegraph.Telegraph:
    client = telegraph.Telegraph()
    client.create_account(short_name="Narumi's Bot")
    return client


def create_page(title: str, **kwargs: Any) -> str:
    """Create a Telegraph page synchronously.

    Note: This blocks the event loop. Use async_create_page() in async contexts.

    Args:
        title: Page title
        **kwargs: Additional arguments passed to Telegraph API

    Returns:
        URL of the created page
    """
    client = get_telegraph_client()
    resp = client.create_page(title=title, **kwargs)
    return resp["url"]


async def async_create_page(title: str, **kwargs: Any) -> str:
    """Create a Telegraph page asynchronously without blocking the event loop.

    Args:
        title: Page title
        **kwargs: Additional arguments passed to Telegraph API

    Returns:
        URL of the created page
    """
    return await asyncio.to_thread(create_page, title, **kwargs)


async def load_url(url: str) -> str:
    with logfire.span("load_url"):
        return await kabigon.load_url(url)


def logfire_is_enabled() -> bool:
    return bool(os.getenv("LOGFIRE_TOKEN"))


def configure_logfire() -> None:
    if not logfire_is_enabled():
        return

    logfire.configure()
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
    logger.info("Configuring OpenTelemetry with Langfuse...")

    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    if public_key is None:
        logger.warning("LANGFUSE_PUBLIC_KEY is not set. Skipping Langfuse configuration.")
        return

    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    if secret_key is None:
        logger.warning("LANGFUSE_SECRET_KEY is not set. Skipping Langfuse configuration.")
        return

    host = os.environ.get("LANGFUSE_HOST")
    if host is None:
        logger.warning("LANGFUSE_HOST is not set. Skipping Langfuse configuration.")
        return

    # Build Basic Auth header.
    langfuse_auth = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()

    # Configure OpenTelemetry endpoint & headers
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = host + "/api/public/otel"
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
