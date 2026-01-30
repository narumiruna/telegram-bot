from __future__ import annotations

from aiogram.types import Message

from .base import BaseCallback
from .utils import safe_callback


class HelpCallback(BaseCallback):
    def __init__(self, helps: list[str]) -> None:
        self.helps = helps

    @safe_callback
    async def __call__(self, message: Message) -> None:
        await message.answer(
            "\n".join(self.helps),
            disable_web_page_preview=True,
        )
