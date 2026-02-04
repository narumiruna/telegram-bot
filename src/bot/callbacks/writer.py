import asyncio
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
from bot.utils.chunk import chunk_on_delimiter

logger = logging.getLogger(__name__)


async def _write_article(text: str) -> Article:
    agent = build_writer_agent()
    result = await Runner.run(agent, input=text)
    return result.final_output_as(Article)


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

        articles = await asyncio.gather(*[_write_article(chunk) for chunk in chunk_on_delimiter(message_text)])
        if len(articles) == 1:
            await articles[0].answer(message)
            return

        text = "\n\n".join([article.content for article in articles])
        article = await _write_article(text)
        await article.answer(message)
