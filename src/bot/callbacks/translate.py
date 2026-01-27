from __future__ import annotations

from aiogram.types import Message
from aiogram.types import Update
from loguru import logger

from .. import chains
from ..presentation import MessageResponse
from .base import BaseCallback
from .utils import get_message_from_update
from .utils import get_processed_message_text
from .utils import safe_callback


class TranslationCallback(BaseCallback):
    def __init__(self, lang: str) -> None:
        self.lang = lang

    @safe_callback
    async def __call__(self, update: Message | Update, context: object | None = None) -> None:
        message = get_message_from_update(update)
        if not message:
            return

        message_text, error = await get_processed_message_text(message, require_url=False)
        if error:
            await message.answer(error)
            return
        if not message_text:
            return

        translated_text = await chains.translate(message_text, target_lang=self.lang)
        logger.info("Translated text to {lang}: {text}", lang=self.lang, text=translated_text)

        response = MessageResponse(
            content=translated_text,
            title="Translation",
            parse_mode=None,  # Plain text
        )
        await response.send(message)
