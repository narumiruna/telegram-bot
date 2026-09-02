from unittest.mock import AsyncMock
from unittest.mock import Mock

import pytest
from aiogram.exceptions import TelegramNetworkError
from aiogram.methods import SendMessage
from aiogram.types import Message

from bot.utils.reply import reply


@pytest.mark.asyncio
async def test_reply_retries_telegram_network_error():
    sent_message = Mock(spec=Message)
    message = Mock(spec=Message)
    message.reply = AsyncMock(
        side_effect=[
            TelegramNetworkError(method=SendMessage(chat_id=1, text="test"), message="connection reset"),
            sent_message,
        ]
    )

    result = await reply(message, "test", parse_mode="HTML")

    assert result is sent_message
    assert message.reply.await_count == 2
    message.reply.assert_awaited_with("test", parse_mode="HTML")


@pytest.mark.asyncio
async def test_reply_does_not_retry_other_errors():
    message = Mock(spec=Message)
    message.reply = AsyncMock(side_effect=ValueError("invalid message"))

    with pytest.raises(ValueError, match="invalid message"):
        await reply(message, "test")

    message.reply.assert_awaited_once_with("test")
