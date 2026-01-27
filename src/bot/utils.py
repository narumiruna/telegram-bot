"""Utility functions for file I/O operations.

This module contains basic file and JSON handling utilities.
For specific functionality, see:
- bot.telegraph_utils: Telegraph page creation and HTML sanitization
- bot.url_parser: URL parsing and extraction
- bot.observability: Logfire and Langfuse configuration
"""

import json
from pathlib import Path
from typing import Any

import kabigon
import logfire

__all__ = [
    # File I/O
    "save_text",
    "load_json",
    "save_json",
    "load_url",
]


async def load_url(url: str) -> str:
    with logfire.span("load_url"):
        return await kabigon.load_url(url)


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
