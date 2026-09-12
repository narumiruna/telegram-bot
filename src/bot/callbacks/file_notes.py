from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from aiogram import Bot
from aiogram.types import Document
from aiogram.types import Message
from kabigon.loaders.pdf import read_pdf_content
from kabigon.loaders.utils import html_to_markdown

from bot.agents.writer import write_article
from bot.callbacks.utils import safe_callback


async def _get_document_text(bot: Bot, document: Document) -> str | None:
    suffix = Path(document.file_name or "").suffix.lower()
    if suffix not in {".pdf", ".html"}:
        return None

    with TemporaryDirectory(prefix="telegram-bot-") as temp_dir:
        file_path = Path(temp_dir) / f"document{suffix}"
        await bot.download(document, destination=file_path)
        return await asyncio.to_thread(_read_document, file_path)


def _read_document(file_path: Path) -> str | None:
    match file_path.suffix:
        case ".pdf":
            return read_pdf_content(file_path)
        case ".html":
            return html_to_markdown(file_path.read_bytes())
        case _:
            return None


@safe_callback
async def file_callback(message: Message, bot: Bot) -> None:
    document = message.document
    if not document:
        return

    text = await _get_document_text(bot, document)
    if not text:
        return

    article = await write_article(text)
    await article.reply(message)
