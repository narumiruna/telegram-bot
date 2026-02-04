import logging

import logfire
from aiogram.filters import CommandObject
from aiogram.types import Message

from bot.agents.writer import write_article
from bot.callbacks.utils import check_message_type
from bot.callbacks.utils import get_processed_message_text
from bot.callbacks.utils import safe_callback

logger = logging.getLogger(__name__)


@safe_callback
async def writer_callback(message: Message, command: CommandObject) -> None:
    check_message_type(message)

    with logfire.span("writer_callback"):
        message_text, error = await get_processed_message_text(message, require_url=False)
        if error:
            await message.answer(error)
            return
        if not message_text:
            return

        article = await write_article(message_text)
        await article.answer(message)
