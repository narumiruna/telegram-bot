from __future__ import annotations

import html
from typing import Final

from aiogram.types import Message
from youtube_search import YoutubeSearch

from .utils import strip_command

MAX_RESULTS: Final[int] = 10


async def search_youtube_callback(message: Message) -> None:
    # Extract command arguments from message text
    text = strip_command(message.text or "")
    if not text:
        return
    
    search_terms = "_".join(text.split())
    result = YoutubeSearch(search_terms=search_terms, max_results=MAX_RESULTS).to_dict()
    if not result:
        return

    if isinstance(result, str):
        await message.answer(result)
        return

    html_content = "\n".join(
        [f'<a href="https://youtu.be/{item["id"]}">{html.escape(item["title"])}</a>' for item in result]
    )
    await message.answer(html_content, parse_mode="HTML")
