import asyncio
import concurrent.futures
import functools
import json
import os
import re
from functools import cache
from pathlib import Path
from typing import Any

import logfire
import telegraph
from kabigon import Compose
from kabigon import FirecrawlLoader
from kabigon import PDFLoader
from kabigon import PlaywrightLoader
from kabigon import ReelLoader
from kabigon import TwitterLoader
from kabigon import YoutubeLoader
from kabigon import YtdlpLoader
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


def create_page(title: str, **kwargs) -> str:
    client = get_telegraph_client()

    resp = client.create_page(title=title, **kwargs)
    return resp["url"]


def async_wrapper(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, func, *args, **kwargs)
            return result

    return wrapper


@cache
def get_composed_loader() -> Compose:
    return Compose(
        [
            TwitterLoader(),
            YoutubeLoader(),
            ReelLoader(),
            YtdlpLoader(),
            PDFLoader(),
            FirecrawlLoader(),
            PlaywrightLoader(timeout=50_000, wait_until="networkidle"),
            PlaywrightLoader(timeout=10_000),
        ]
    )


def load_url(url: str) -> str:
    loader = get_composed_loader()
    return loader.load(url)


async def async_load_url(url: str) -> str:
    loader = get_composed_loader()
    return await loader.async_load(url)


def logfire_is_enabled() -> bool:
    return bool(os.getenv("LOGFIRE_TOKEN"))


def configure_logfire() -> None:
    if not logfire_is_enabled():
        return

    logfire.configure()
    logger.configure(handlers=[logfire.loguru_handler()])
