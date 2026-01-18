"""Utility functions for file I/O operations.

This module contains basic file and JSON handling utilities.
For specific functionality, see:
- telegraph_utils.py: Telegraph page creation and HTML sanitization
- url_parser.py: URL parsing and extraction
- observability.py: Logfire and Langfuse configuration
"""

import json
from pathlib import Path
from typing import Any

# Backward compatibility: re-export functions from new modules
from .observability import configure_langfuse
from .observability import configure_logfire
from .observability import load_url
from .observability import logfire_is_enabled
from .telegraph_utils import async_create_page
from .telegraph_utils import create_page
from .telegraph_utils import get_telegraph_client
from .telegraph_utils import sanitize_telegraph_html
from .url_parser import parse_url
from .url_parser import parse_urls

__all__ = [
    # File I/O
    "save_text",
    "load_json",
    "save_json",
    # URL parsing (re-exported from url_parser)
    "parse_url",
    "parse_urls",
    # Telegraph (re-exported from telegraph_utils)
    "get_telegraph_client",
    "sanitize_telegraph_html",
    "create_page",
    "async_create_page",
    # Observability (re-exported from observability)
    "load_url",
    "logfire_is_enabled",
    "configure_logfire",
    "configure_langfuse",
]


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
