from __future__ import annotations

from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from .. import chains
from .utils import get_processed_message_text
from .utils import safe_callback


@safe_callback
async def summarize_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    text, error = await get_processed_message_text(message, require_url=True)
    if error:
        await message.reply_text(error)
        return
    if not text:
        return

    response = await chains.summarize(text)

    logger.info("Summarized text: {text}", text=response.content)
    await response.send(message)
