from __future__ import annotations

import html

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
