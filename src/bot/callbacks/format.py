from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from .. import chains
from .utils import get_processed_message_text
from .utils import safe_callback


@safe_callback
async def format_callback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    message_text, error = await get_processed_message_text(message, require_url=False)
    if error:
        await message.reply_text(error)
        return
    if not message_text:
        return

    article = await chains.format(message_text)
    response = article.to_message_response()

    await response.send(message)
