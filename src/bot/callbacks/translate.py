from __future__ import annotations

from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from .. import chains
from ..constants import MAX_MESSAGE_LENGTH
from ..utils import create_page
from .utils import get_processed_message_text
from .utils import safe_callback


class TranslationCallback:
    def __init__(self, lang: str) -> None:
        self.lang = lang

    @safe_callback
    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        if not message:
            return

        message_text, error = await get_processed_message_text(message, require_url=False)
        if error:
            await message.reply_text(error)
            return
        if not message_text:
            return

        reply_text = await chains.translate(message_text, lang=self.lang)
        logger.info("Translated text to {lang}: {text}", lang=self.lang, text=reply_text)

        if len(reply_text) > MAX_MESSAGE_LENGTH:
            reply_text = create_page(title="Translation", html_content=reply_text.replace("\n", "<br>"))
        await message.reply_text(reply_text)
