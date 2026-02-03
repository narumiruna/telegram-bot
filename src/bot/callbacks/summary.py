from __future__ import annotations

import logging

from aiogram.types import Message
from aiogram.types import Update

from bot import chains

from .utils import get_message_from_update
from .utils import get_processed_message_text
from .utils import safe_callback

logger = logging.getLogger(__name__)


@safe_callback
async def summarize_callback(update: Message | Update, context: object | None = None) -> None:
    message = get_message_from_update(update)
    if not message:
        return

    text, error = await get_processed_message_text(message, require_url=True)
    if error:
        await message.answer(error)
        return
    if not text:
        return

    response = await chains.summarize(text)

    logger.info("Summarized text: %s", response.content)
    await response.send(message)
