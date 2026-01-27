"""Presentation layer for formatting and sending bot responses.

This module provides a unified interface for sending messages to users,
automatically handling Telegraph page creation for long messages.
"""

from __future__ import annotations

import asyncio
import html
from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast
from unittest.mock import AsyncMock

from aiogram.types import Message

from .constants import MAX_MESSAGE_LENGTH
from .utils import async_create_page


@dataclass
class MessageResponse:
    """A response message that can be sent to Telegram.

    Automatically creates a Telegraph page for long messages to avoid
    Telegram's message length limit.

    Attributes:
        content: The message content (plain text or HTML)
        title: Optional title for Telegraph page
        parse_mode: Telegram parse mode ('HTML', 'Markdown', or None)
    """

    content: str
    title: str | None = None
    parse_mode: str | None = "HTML"

    async def send(self, message: Message) -> Message:
        """Send response to Telegram.

        If content exceeds MAX_MESSAGE_LENGTH, creates a Telegraph page
        and sends the URL instead.

        Args:
            message: The Telegram message to reply to

        Returns:
            The sent message
        """
        answer = getattr(message, "answer", None)
        reply_text = getattr(message, "reply_text", None)

        def is_async_callable(func: object | None) -> bool:
            return isinstance(func, AsyncMock) or asyncio.iscoroutinefunction(func)

        send_direct: Callable[..., Awaitable[Message]]
        if is_async_callable(answer):
            send_direct = cast(Callable[..., Awaitable[Message]], answer)
        elif is_async_callable(reply_text):
            send_direct = cast(Callable[..., Awaitable[Message]], reply_text)
        elif callable(answer):
            send_direct = cast(Callable[..., Awaitable[Message]], answer)
        elif callable(reply_text):
            send_direct = cast(Callable[..., Awaitable[Message]], reply_text)
        else:
            raise AttributeError("Message has no async send method (answer/reply_text)")
        if len(self.content) > MAX_MESSAGE_LENGTH:
            # Create Telegraph page for long content
            telegraph_html = (
                html.escape(self.content).replace("\n", "<br>")
                if self.parse_mode is None
                else self.content.replace("\n", "<br>")
            )
            url = await async_create_page(
                title=self.title or "Response",
                html_content=telegraph_html,
            )
            return await send_direct(url)
        else:
            # Send directly for short content
            return await send_direct(self.content, parse_mode=self.parse_mode)
