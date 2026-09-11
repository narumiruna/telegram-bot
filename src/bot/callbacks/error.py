import html
import json
import logging
import traceback

from aiogram import Bot
from aiogram.types import CallbackQuery
from aiogram.types import ErrorEvent
from aiogram.types import Message

from bot.agents.error import ErrorExplanation
from bot.agents.error import explain_error
from bot.agents.error import fallback_error_explanation
from bot.core import MessageResponse
from bot.settings import settings
from bot.utils.page import async_create_page

logger = logging.getLogger(__name__)


def _get_originating_message(event: ErrorEvent) -> Message | None:
    try:
        update_event = event.update.event
    except LookupError:
        return None

    if isinstance(update_event, Message):
        return update_event
    if isinstance(update_event, CallbackQuery) and isinstance(update_event.message, Message):
        return update_event.message
    return None


async def _get_explanation(error: Exception) -> ErrorExplanation:
    try:
        return await explain_error(error)
    except Exception:
        logger.exception("Error explanation agent failed.")
        return fallback_error_explanation(error)


async def _notify_user(message: Message | None, explanation: ErrorExplanation) -> None:
    if message is None:
        return

    try:
        await MessageResponse(content=explanation.user_message).reply(message, parse_mode=None)
    except Exception:
        logger.exception("Failed to send error explanation to user.")


def _build_diagnostics_html(event: ErrorEvent) -> str:
    update_str = event.update.model_dump() if event.update else {}
    html_content = (
        "An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}</pre>\n\n"
        f"<pre>exception = {html.escape(str(event.exception))}</pre>\n\n"
    )
    if event.exception:
        tb_list = traceback.format_exception(None, event.exception, event.exception.__traceback__)
        tb_string = "".join(tb_list)
        html_content += f"<pre>Traceback (most recent call last):\n{html.escape(tb_string)}</pre>"
    return html_content


async def _notify_administrator(event: ErrorEvent, bot: Bot, explanation: ErrorExplanation) -> None:
    if settings.developer_chat_id is None:
        return

    try:
        page_url = await async_create_page(title="Error", html_content=_build_diagnostics_html(event))
    except Exception:
        logger.exception("Failed to create error diagnostics page.")
        page_url = None

    notification = f"錯誤摘要：{explanation.administrator_message}"
    if page_url:
        notification += f"\n\n診斷資料：{page_url}"
    else:
        notification += "\n\n診斷資料頁建立失敗，請查看服務日誌。"

    try:
        await bot.send_message(chat_id=settings.developer_chat_id, text=notification)
    except Exception:
        logger.exception("Failed to send error explanation to administrator.")


async def error_callback(event: ErrorEvent, bot: Bot) -> None:
    logger.error("Exception while handling an update: %s", event.exception)

    explanation = await _get_explanation(event.exception)
    await _notify_user(_get_originating_message(event), explanation)
    await _notify_administrator(event, bot, explanation)
