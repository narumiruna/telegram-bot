from __future__ import annotations

import os

from kabigon.loaders.pdf import read_pdf_content
from kabigon.loaders.utils import read_html_content
from telegram import Update
from telegram.ext import ContextTypes

from .. import chains
from .utils import safe_callback


@safe_callback
async def file_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    document = message.document
    if not document:
        return

    new_file = await context.bot.get_file(document.file_id)
    file_path = await new_file.download_to_drive()

    match file_path.suffix:
        case ".pdf":
            text = read_pdf_content(file_path)
        case ".html":
            text = read_html_content(file_path)
        case _:
            text = None

    os.remove(file_path)

    if not text:
        return

    article = await chains.format(text)
    response = article.to_message_response()

    await response.send(message)
