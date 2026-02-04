import logging

import logfire
from agents import Runner
from aiogram.filters import CommandObject
from aiogram.types import Message

from bot.agents.writer import Article
from bot.agents.writer import build_writer_agent
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

        agent = build_writer_agent()
        result = await Runner.run(agent, input=message_text)

        article = result.final_output_as(Article)
        await article.answer(message)
