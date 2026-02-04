from __future__ import annotations

import html
import logging

from aiogram.types import Message
from pydantic import BaseModel

from bot.settings import settings
from bot.utils.page import async_create_page

logger = logging.getLogger(__name__)


class MessageResponse(BaseModel):
    content: str
    title: str | None = None

    def build_text(self) -> str:
        if self.title:
            return f"📝 {self.title}\n\n{self.content}"
        return self.content

    async def answer(self, message: Message, parse_mode: str | None = "HTML") -> Message:
        if len(self.content) <= settings.max_message_length:
            return await message.answer(self.build_text(), parse_mode=parse_mode)

        logger.info("Content too long, uploading to Telegraph")
        telegraph_html = (
            html.escape(self.content).replace("\n", "<br>")
            if parse_mode is None
            else self.content.replace("\n", "<br>")
        )
        url = await async_create_page(
            title=self.title or "Response",
            html_content=telegraph_html,
        )
        return await message.answer(url)
