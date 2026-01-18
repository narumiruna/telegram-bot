import asyncio
import functools
from html import escape as html_escape
from html.parser import HTMLParser
from typing import Any

import telegraph


@functools.cache
def get_telegraph_client() -> telegraph.Telegraph:
    client = telegraph.Telegraph()
    client.create_account(short_name="Narumi's Bot")
    return client


_TELEGRAPH_ALLOWED_TAGS: set[str] = {
    "a",
    "aside",
    "b",
    "blockquote",
    "br",
    "code",
    "em",
    "figcaption",
    "figure",
    "h3",
    "h4",
    "hr",
    "i",
    "iframe",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "s",
    "strong",
    "u",
    "ul",
    "video",
}

_TELEGRAPH_VOID_TAGS: set[str] = {"br", "hr", "img"}

_TELEGRAPH_TAG_REMAP: dict[str, str] = {
    "del": "s",
    "h1": "h3",
    "h2": "h3",
    "h5": "h4",
    "h6": "h4",
    "strike": "s",
}

_TELEGRAPH_ALLOWED_ATTRS: dict[str, set[str]] = {
    "a": {"href"},
    "iframe": {"src"},
    "img": {"src", "alt"},
    "video": {"src"},
}


class _TelegraphHTMLSanitizer(HTMLParser):
    """Tolerant sanitizer for Telegraph's limited HTML subset."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._open_tags: list[str] = []

    def get_html(self) -> str:
        for tag in reversed(self._open_tags):
            self._parts.append(f"</{tag}>")
        return "".join(self._parts)

    def handle_data(self, data: str) -> None:
        self._parts.append(html_escape(data, quote=False))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        mapped = _TELEGRAPH_TAG_REMAP.get(tag, tag)
        if mapped not in _TELEGRAPH_ALLOWED_TAGS:
            self._parts.append(html_escape(self.get_starttag_text() or f"<{tag}>", quote=False))
            return

        attr_allowlist = _TELEGRAPH_ALLOWED_ATTRS.get(mapped, set())
        rendered_attrs: list[str] = []
        for key, value in attrs:
            if key not in attr_allowlist:
                continue
            if value is None:
                continue
            rendered_attrs.append(f'{key}="{html_escape(value, quote=True)}"')

        attrs_str = (" " + " ".join(rendered_attrs)) if rendered_attrs else ""
        self._parts.append(f"<{mapped}{attrs_str}>")

        if mapped not in _TELEGRAPH_VOID_TAGS:
            self._open_tags.append(mapped)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        mapped = _TELEGRAPH_TAG_REMAP.get(tag, tag)
        if mapped in _TELEGRAPH_VOID_TAGS:
            return

        if mapped not in _TELEGRAPH_ALLOWED_TAGS:
            self._parts.append(html_escape(f"</{tag}>", quote=False))
            return

        if not self._open_tags or self._open_tags[-1] != mapped:
            self._parts.append(html_escape(f"</{tag}>", quote=False))
            return

        self._open_tags.pop()
        self._parts.append(f"</{mapped}>")


def sanitize_telegraph_html(html_content: str) -> str:
    """Convert arbitrary HTML into Telegraph-compatible HTML (best-effort)."""
    parser = _TelegraphHTMLSanitizer()
    parser.feed(html_content)
    parser.close()
    return parser.get_html()


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
    if isinstance(kwargs.get("html_content"), str):
        kwargs["html_content"] = sanitize_telegraph_html(kwargs["html_content"])
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
