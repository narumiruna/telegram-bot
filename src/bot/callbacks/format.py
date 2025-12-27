from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from .. import chains
from ..constants import MAX_MESSAGE_LENGTH
from ..utils import async_create_page
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

    result = await chains.format(message_text)

    if len(str(result)) > MAX_MESSAGE_LENGTH:
        text = await async_create_page(title=result.title, html_content=str(result).replace("\n", "<br>"))
    else:
        text = str(result)

    await message.reply_text(text)
