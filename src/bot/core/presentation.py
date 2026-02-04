from __future__ import annotations

import asyncio
import html
from collections.abc import Awaitable
from collections.abc import Callable
from typing import cast
from unittest.mock import AsyncMock

from aiogram.types import Message
from pydantic import BaseModel

from bot.settings import settings
from bot.utils.page import async_create_page


class MessageResponse(BaseModel):
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

    def build_text(self) -> str:
        if self.title:
            return f"📝 {self.title}\n\n{self.content}"
        return self.content

    async def answer(self, message: Message) -> Message:
        if len(self.content) > settings.max_message_length:
            telegraph_html = (
                html.escape(self.content).replace("\n", "<br>")
                if self.parse_mode is None
                else self.content.replace("\n", "<br>")
            )
            url = await async_create_page(
                title=self.title or "Response",
                html_content=telegraph_html,
            )
            return await message.answer(url)

        return await message.answer(self.build_text(), parse_mode=self.parse_mode)

    async def send(self, message: Message) -> Message:
        """Send response to Telegram.

        If content exceeds the max message length setting, creates a Telegraph page
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
        if len(self.content) > settings.max_message_length:
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
        # Send directly for short content
        return await send_direct(self.content, parse_mode=self.parse_mode)
