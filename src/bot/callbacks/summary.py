from __future__ import annotations

from loguru import logger
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .. import chains
from ..utils import async_load_url
from ..utils import parse_url
from .utils import get_message_text


async def summarize_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    message_text = get_message_text(message)
    if not message_text:
        return
    logger.info("Message text: {text}", text=message_text)

    url = parse_url(message_text)
    if not url:
        return
    logger.info("Parsed URL: {url}", url=url)

    try:
        text = await async_load_url(url)
    except Exception as e:
        logger.warning("Failed to load URL: {url}, got error: {error}", url=url, error=e)
        await message.reply_text(f"Failed to load URL: {url}")
        return

    result = await chains.summarize(text)

    logger.info("Summarized text: {text}", text=result)
    await message.reply_text(result, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
