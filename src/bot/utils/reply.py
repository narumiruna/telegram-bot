import logging
from typing import Any

from aiogram.exceptions import TelegramNetworkError
from aiogram.types import Message
from tenacity import before_sleep_log
from tenacity import retry
from tenacity import retry_if_exception_type
from tenacity import stop_after_attempt
from tenacity import wait_exponential
from tenacity import wait_random

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=4) + wait_random(0, 0.1),
    retry=retry_if_exception_type(TelegramNetworkError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def reply(message: Message, text: str, **kwargs: Any) -> Message:
    """Reply to a Telegram message, retrying transient network failures."""
    return await message.reply(text, **kwargs)
