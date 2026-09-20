import asyncio
import logging
import re
from collections.abc import Awaitable
from collections.abc import Callable
from functools import wraps

from aiogram.types import Message

from bot.utils.url import load_url

logger = logging.getLogger(__name__)


def parse_urls(s: str) -> list[str]:
    """Parse all URLs from the given string.

    Args:
        s: String that may contain URLs

    Returns:
        List of URLs found in the string
    """
    url_pattern = r"https?://[^\s]+"
    return re.findall(url_pattern, s)


def get_user_display_name(message: Message) -> str | None:
    """Get the user's display name.

    For example:
        User(first_name='なるみ', id=123456789, is_bot=False, language_code='zh-hans', username='narumi')
        -> なるみ(narumi): Hello, world!

    Args:
        message (Message): The message object

    Returns:
        str | None: The user's display name
    """
    user = message.from_user
    if not user:
        return None

    if not user.username:
        return user.first_name

    return f"{user.first_name}({user.username})"


def _get_message_text(message: Message, include_user_name: bool = False) -> str:
    message_text = strip_command(message.text or message.caption or "")
    if not message_text or not include_user_name:
        return message_text

    name = get_user_display_name(message)
    return f"{name}: {message_text}" if name else message_text


def append_url_contents(message_text: str, url_contents: list[tuple[str, str]]) -> str:
    """Append loaded URL content after the original message text."""
    sections = [message_text]
    for url, content in url_contents:
        sections.append(f"URL content from {url}:\n{content}")
    return "\n\n".join(sections)


def strip_command(text: str) -> str:
    """Remove the command from the text.
    For example:
    Input: "/sum 1 2 3"
    Output: "1 2 3"

    Input: "hello"
    Output: "hello"
    """
    if text.startswith("/"):
        _command, *args = text.split(" ", 1)
        return args[0] if args else ""
    return text


async def get_processed_message_text(
    message: Message,
    require_url: bool = False,
    include_reply_to_message: bool = True,
    include_user_name: bool = False,
) -> tuple[str | None, str | None]:
    """取得訊息文字，並處理 URL 載入（如果存在）

    支援多個 URL 的處理，會並行載入所有 URL 的內容並組合。

    Args:
        message: Telegram message
        require_url: 是否必須包含 URL

    Returns:
        (處理後的文字, 錯誤訊息)
        如果成功: (text, None)
        如果失敗: (None, error_message)
    """
    current_message_text = _get_message_text(message, include_user_name=include_user_name)
    reply_message_text = ""
    if include_reply_to_message and message.reply_to_message:
        reply_message_text = _get_message_text(message.reply_to_message, include_user_name=include_user_name)

    if not current_message_text and not reply_message_text:
        return None, None

    if current_message_text and reply_message_text:
        message_text = f"Replied message:\n{reply_message_text}\n\nCurrent message:\n{current_message_text}"
    else:
        message_text = reply_message_text or current_message_text

    logger.info("Message text: %s", message_text)
    urls = parse_urls(message_text)

    # 如果要求 URL 但沒有找到
    if require_url and not urls:
        return None, None

    # 如果沒有 URL，直接返回原始文字
    if not urls:
        return message_text, None

    # 嘗試載入所有 URL
    logger.info("Parsed URLs: %s", urls)
    try:
        # 並行載入所有 URL
        contents = await asyncio.gather(*[load_url(url) for url in urls])
    except asyncio.CancelledError:
        logger.debug("URL loading cancelled.")
        raise
    except Exception as e:
        error_msg = f"Failed to load URL(s): {', '.join(urls)}"
        logger.warning("%s, got error: %s", error_msg, e)
        return None, error_msg
    else:
        combined_content = append_url_contents(message_text, list(zip(urls, contents, strict=True)))
        return combined_content, None


def safe_callback[**P, R](callback_func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    """Log callback failures and re-raise them for the global error handler.

    Preserve the callback's signature, return value, and cancellation behavior.
    """

    @wraps(callback_func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await callback_func(*args, **kwargs)
        except asyncio.CancelledError:
            logger.info("Callback %s cancelled.", wrapper.__name__)
            raise
        except Exception as e:
            logger.exception("Error in callback %s: %s", wrapper.__name__, e)
            raise

    return wrapper
