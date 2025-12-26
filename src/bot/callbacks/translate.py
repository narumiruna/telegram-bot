from __future__ import annotations

from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from .. import chains
from ..constants import MAX_MESSAGE_LENGTH
from ..utils import async_load_url
from ..utils import create_page
from ..utils import parse_url
from .utils import get_message_text


class TranslationCallback:
    def __init__(self, lang: str) -> None:
        self.lang = lang

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        if not message:
            return

        message_text = get_message_text(message)
        if not message_text:
            return

        url = parse_url(message_text)
        if url:
            message_text = await async_load_url(url)

        reply_text = await chains.translate(message_text, lang=self.lang)
        logger.info("Translated text to {lang}: {text}", lang=self.lang, text=reply_text)

        if len(reply_text) > MAX_MESSAGE_LENGTH:
            reply_text = create_page(title="Translation", html_content=reply_text.replace("\n", "<br>"))
        await message.reply_text(reply_text)
