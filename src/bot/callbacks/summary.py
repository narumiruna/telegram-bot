from __future__ import annotations

from aiogram.types import Message
from loguru import logger

from .. import chains
from .utils import get_processed_message_text
from .utils import safe_callback


@safe_callback
async def summarize_callback(message: Message) -> None:
    text, error = await get_processed_message_text(message, require_url=True)
    if error:
        await message.answer(error)
        return
    if not text:
        await message.answer("請提供要摘要的 URL，例如：/s https://example.com")
        return

    response = await chains.summarize(text)

    logger.info("Summarized text: {text}", text=response.content)
    await response.send(message)
