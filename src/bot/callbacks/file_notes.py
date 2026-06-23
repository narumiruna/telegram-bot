from __future__ import annotations

import contextlib
import os
from collections.abc import Awaitable
from collections.abc import Callable
from pathlib import Path
from typing import cast

from aiogram import Bot
from aiogram.types import Document
from aiogram.types import Message
from kabigon.loaders.pdf import read_pdf_content
from kabigon.loaders.utils import read_html_content

from bot.agents.writer import write_article
from bot.callbacks.utils import safe_callback


async def _download_document(bot: Bot, document: Document) -> Path | None:
    file = await bot.get_file(document.file_id)
    download_to_drive = getattr(file, "download_to_drive", None)
    if download_to_drive is None:
        return None
    file_path = await cast(Callable[[], Awaitable[Path | str | None]], download_to_drive)()
    if not file_path:
        return None
    return Path(file_path)


def _read_document(file_path: Path) -> str | None:
    match file_path.suffix:
        case ".pdf":
            return read_pdf_content(file_path)
        case ".html":
            return read_html_content(file_path)
        case _:
            return None


@safe_callback
async def file_callback(message: Message, bot: Bot) -> None:
    document = message.document
    if not document:
        return

    file_path = await _download_document(bot, document)
    if not file_path:
        return
    try:
        text = _read_document(file_path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.remove(file_path)

    if not text:
        return

    article = await write_article(text)
    await article.reply(message)
