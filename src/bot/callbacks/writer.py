from agents import Runner
from aiogram.types import Message
from aiogram.types import Update

from bot.agents.writer import Article
from bot.agents.writer import build_writer_agent
from bot.callbacks.utils import get_message_from_update
from bot.callbacks.utils import get_processed_message_text
from bot.callbacks.utils import safe_callback


@safe_callback
async def writer_callback(update: Message | Update) -> None:
    message = get_message_from_update(update)
    if not message:
        return

    message_text, error = await get_processed_message_text(message, require_url=False)
    if error:
        await message.answer(error)
        return
    if not message_text:
        return

    agent = build_writer_agent()
    result = await Runner.run(agent, input=message_text)

    article = result.final_output_as(Article)
    response = article.to_message_response()
    await response.send(message)
