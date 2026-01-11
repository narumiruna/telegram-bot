"""Presentation layer for formatting and sending bot responses.

This module provides a unified interface for sending messages to users,
automatically handling Telegraph page creation for long messages.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

from telegram import Message

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

    async def send(self, message: Message) -> None:
        """Send the response to Telegram.

        If the content exceeds MAX_MESSAGE_LENGTH, creates a Telegraph page
        and sends the URL instead.

        Args:
            message: The Telegram message to reply to
        """
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
            await message.reply_text(url)
        else:
            # Send directly for short content
            await message.reply_text(self.content, parse_mode=self.parse_mode)
