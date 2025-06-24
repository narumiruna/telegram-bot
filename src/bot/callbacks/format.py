from __future__ import annotations

from typing import Final

from telegram import Update
from telegram.ext import ContextTypes

from .. import chains
from ..utils import async_load_url
from ..utils import create_page
from ..utils import parse_url
from .utils import get_message_text

MAX_LENGTH: Final[int] = 1_000


async def format_callback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    message_text = get_message_text(message)
    if not message_text:
        return

    url = parse_url(message_text)
    if url:
        message_text = await async_load_url(url)

    result = await chains.format(message_text)

    if len(str(result)) > MAX_LENGTH:
        text = create_page(title=result.title, html_content=str(result).replace("\n", "<br>"))
    else:
        text = str(result)

    await message.reply_text(text)
