from __future__ import annotations

from aiogram.types import Message

from .. import chains
from .utils import get_processed_message_text
from .utils import safe_callback


@safe_callback
async def format_callback(message: Message) -> None:
    message_text, error = await get_processed_message_text(message, require_url=False)
    if error:
        await message.answer(error)
        return
    if not message_text:
        return

    article = await chains.format(message_text)
    response = article.to_message_response()

    await response.send(message)
