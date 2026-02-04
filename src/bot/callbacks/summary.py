from __future__ import annotations

import logging

import logfire
from aiogram.filters import CommandObject
from aiogram.types import Message

from bot.agents.summary import summarize
from bot.callbacks.utils import check_message_type
from bot.callbacks.utils import get_processed_message_text
from bot.callbacks.utils import safe_callback

logger = logging.getLogger(__name__)


@safe_callback
async def summarize_callback(message: Message, command: CommandObject) -> None:
    check_message_type(message)

    with logfire.span("summarize_callback"):
        text, error = await get_processed_message_text(message, require_url=True)
        if error:
            await message.answer(error)
            return
        if not text:
            return

        article = await summarize(text)
        await article.answer(message)
