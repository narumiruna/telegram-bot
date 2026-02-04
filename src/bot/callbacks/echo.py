from __future__ import annotations

import html
import json

from aiogram.types import Message


async def echo_callback(message: Message) -> None:
    text = html.escape(
        json.dumps(
            message.model_dump(),
            indent=2,
            ensure_ascii=False,
        )
    )

    if len(text) > 4096:
        text = text[:4096] + "\n..."

    await message.answer(
        text=f"<blockquote expandable>{text}</blockquote>",
        parse_mode="HTML",
    )
