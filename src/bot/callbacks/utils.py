import asyncio
import logging
from functools import wraps
from typing import Any

from aiogram.types import Message
from aiogram.types import Update

from bot.url_parser import parse_urls
from bot.utils import load_url

logger = logging.getLogger(__name__)


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


def get_message_text(
    message: Message,
    include_reply_to_message: bool = True,
    include_user_name: bool = False,
) -> str:
    message_text = getattr(message, "text", None) or getattr(message, "caption", None) or ""
    message_text = strip_command(message_text)

    if include_user_name:
        name = get_user_display_name(message)
        if name:
            message_text = f"{name}: {message_text}"

    if include_reply_to_message:
        reply_to_message = getattr(message, "reply_to_message", None)
        if reply_to_message:
            reply_to_message_text = get_message_text(
                reply_to_message,
                include_reply_to_message=False,
                include_user_name=include_user_name,
            )
            if reply_to_message_text:
                message_text = f"{reply_to_message_text}\n\n{message_text}"

    logger.info("Message text: %s", message_text)
    return message_text


def _is_message_like(obj: Any) -> bool:
    if obj is None:
        return False
    if hasattr(obj, "message") and not isinstance(obj, Message):
        return False
    return isinstance(obj, Message) or hasattr(obj, "answer") or hasattr(obj, "reply_text")


def _extract_message(args: tuple[Any, ...]) -> Message | None:
    for arg in args:
        if _is_message_like(arg):
            return arg
    for arg in args:
        message = getattr(arg, "message", None)
        if _is_message_like(message):
            return message
    return None


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


def get_message_key(message: Message) -> str:
    return f"{message.message_id}:{message.chat.id}"


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
    message_text = get_message_text(
        message,
        include_reply_to_message=include_reply_to_message,
        include_user_name=include_user_name,
    )
    if not message_text:
        return None, None

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
        # 組合所有內容
        if len(contents) == 1:
            return contents[0], None
        # 多個 URL 時，用分隔符組合內容
        combined_content = "\n\n---\n\n".join(contents)
        return combined_content, None


def safe_callback(callback_func):
    """統一錯誤處理裝飾器

    包裝 callback 函數，捕捉並處理執行期間的例外：
    1. 通知用戶發生錯誤
    2. 記錄完整錯誤訊息供除錯
    3. 重新拋出例外讓全域錯誤處理器可以處理

    Args:
        callback_func: 要包裝的 async callback 函數或方法

    Returns:
        包裝後的函數

    Example:
        @safe_callback
        async def my_callback(message: Message) -> None:
            # callback implementation
            pass

        class MyCallback:
            @safe_callback
            async def __call__(self, message: Message) -> None:
                # callback implementation
                pass
    """

    @wraps(callback_func)
    async def wrapper(*args, **kwargs):
        message = _extract_message(args)

        try:
            return await callback_func(*args, **kwargs)
        except asyncio.CancelledError:
            logger.info("Callback %s cancelled.", callback_func.__name__)
            raise
        except Exception as e:
            # 記錄錯誤
            logger.exception(
                "Error in callback %s: %s",
                callback_func.__name__,
                str(e),
            )

            # 通知用戶
            if message:
                try:
                    await message.answer("抱歉，處理您的請求時發生錯誤，請稍後再試。\n如果問題持續發生，請聯絡管理員。")
                except Exception as reply_error:
                    logger.error(
                        "Failed to send error message to user: %s",
                        str(reply_error),
                    )

            # 重新拋出例外讓全域錯誤處理器處理
            raise

    return wrapper


def get_message_from_update(update_or_message: Message | Update | None) -> Message | None:
    if update_or_message is None:
        return None
    message = getattr(update_or_message, "message", None)
    if message is not None and (
        isinstance(message, Message) or hasattr(message, "answer") or hasattr(message, "reply_text")
    ):
        return message
    if isinstance(update_or_message, Message):
        return update_or_message
    return None
