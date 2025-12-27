from loguru import logger
from telegram import Message

from ..utils import async_load_url
from ..utils import parse_url


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
    message_text = message.text or ""
    message_text = strip_command(message_text)

    if include_user_name:
        name = get_user_display_name(message)
        if name:
            message_text = f"{name}: {message_text}"

    if include_reply_to_message:
        reply_to_message = message.reply_to_message
        if reply_to_message:
            reply_to_message_text = get_message_text(
                reply_to_message,
                include_reply_to_message=False,
                include_user_name=include_user_name,
            )
            if reply_to_message_text:
                message_text = f"{reply_to_message_text}\n\n{message_text}"

    logger.info("Message text: {text}", text=message_text)
    return message_text


def strip_command(text: str) -> str:
    """Remove the command from the text.
    For example:
    Input: "/sum 1 2 3"
    Output: "1 2 3"

    Input: "hello"
    Output: "hello"
    """
    if text.startswith("/"):
        command, *args = text.split(" ", 1)
        return args[0] if args else ""
    return text


def get_message_key(message: Message) -> str:
    return f"{message.message_id}:{message.chat.id}"


async def get_processed_message_text(
    message: Message,
    require_url: bool = False,
) -> tuple[str | None, str | None]:
    """取得訊息文字，並處理 URL 載入（如果存在）

    Args:
        message: Telegram message
        require_url: 是否必須包含 URL

    Returns:
        (處理後的文字, 錯誤訊息)
        如果成功: (text, None)
        如果失敗: (None, error_message)
    """
    message_text = get_message_text(message)
    if not message_text:
        return None, None

    url = parse_url(message_text)

    # 如果要求 URL 但沒有找到
    if require_url and not url:
        return None, None

    # 如果沒有 URL，直接返回原始文字
    if not url:
        return message_text, None

    # 嘗試載入 URL
    logger.info("Parsed URL: {url}", url=url)
    try:
        content = await async_load_url(url)
        return content, None
    except Exception as e:
        error_msg = f"Failed to load URL: {url}"
        logger.warning("{error}, got error: {exception}", error=error_msg, exception=e)
        return None, error_msg
