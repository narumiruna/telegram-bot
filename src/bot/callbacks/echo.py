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
    await message.answer(
        text=f"<pre>{text}</pre>",
        parse_mode="HTML",
    )
