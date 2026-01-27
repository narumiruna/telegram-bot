from __future__ import annotations

import contextlib
import os
from pathlib import Path

from aiogram import Bot
from aiogram.types import Message
from kabigon.loaders.pdf import read_pdf_content
from kabigon.loaders.utils import read_html_content

from .. import chains
from .utils import safe_callback


@safe_callback
async def file_callback(message: Message, bot: Bot) -> None:
    document = message.document
    if not document:
        return

    file = await bot.get_file(document.file_id)
    if not file.file_path:
        return
    
    # Download file
    file_path = Path(f"/tmp/{document.file_name}")
    await bot.download_file(file.file_path, file_path)
    
    try:
        match file_path.suffix:
            case ".pdf":
                text = read_pdf_content(file_path)
            case ".html":
                text = read_html_content(file_path)
            case _:
                text = None
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.remove(file_path)

    if not text:
        return

    article = await chains.format(text)
    response = article.to_message_response()

    await response.send(message)
