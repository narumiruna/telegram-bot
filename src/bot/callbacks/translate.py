from __future__ import annotations

from collections.abc import Awaitable
from collections.abc import Callable

import logfire
from aiogram.types import Message

from bot.agents.translation import translate
from bot.callbacks.utils import get_processed_message_text
from bot.callbacks.utils import safe_callback


def generate_translation_callback(lang: str) -> Callable[[Message], Awaitable[None]]:
    @safe_callback
    async def callback(message: Message) -> None:
        with logfire.span("translation_callback"):
            message_text, error = await get_processed_message_text(message, require_url=False)
            if error:
                await message.answer(error)
                return
            if not message_text:
                return

            translated_article = await translate(message_text, lang=lang)
            await translated_article.reply(message)

    return callback
