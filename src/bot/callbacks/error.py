from __future__ import annotations

import html
import json
import logging
import traceback

from aiogram import Bot
from aiogram.types import ErrorEvent

from bot.telegraph_utils import async_create_page

logger = logging.getLogger(__name__)


class ErrorCallback:
    def __init__(self, chat_id: str | None = None) -> None:
        self.chat_id = chat_id

    async def __call__(self, event: ErrorEvent, bot: Bot) -> None:
        logger.error("Exception while handling an update: %s", event.exception)

        if self.chat_id is None:
            return

        update_str = event.update.model_dump() if event.update else {}

        html_content = (
            "An exception was raised while handling an update\n"
            f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}</pre>\n\n"
            f"<pre>exception = {html.escape(str(event.exception))}</pre>\n\n"
        )
        if event.exception:
            tb_list = traceback.format_exception(None, event.exception, event.exception.__traceback__)
            tb_string = "".join(tb_list)
            html_content += f"<pre>Traceback (most recent call last):\n{html.escape(tb_string)}</pre>"

        page_url = await async_create_page(title="Error", html_content=html_content)

        await bot.send_message(chat_id=self.chat_id, text=page_url)
