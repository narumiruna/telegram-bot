from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from aiogram.filters import CommandObject
from aiogram.types import Message

from bot.callbacks.writer import writer_callback


@pytest.mark.asyncio
@patch("bot.callbacks.writer.write_article", new_callable=AsyncMock)
@patch("bot.callbacks.writer.get_processed_message_text", new_callable=AsyncMock)
async def test_writer_callback_replies_with_created_page_url(mock_get_processed_message_text, mock_write_article):
    mock_get_processed_message_text.return_value = ("整理這段內容", None)

    article = Mock()
    article.reply = AsyncMock()
    mock_write_article.return_value = article

    message = Mock(spec=Message)
    message.reply = AsyncMock()
    message.answer = AsyncMock()

    await writer_callback(message, Mock(spec=CommandObject))

    mock_write_article.assert_awaited_once_with("整理這段內容")
    article.reply.assert_awaited_once_with(message)
    message.reply.assert_not_called()
    message.answer.assert_not_called()


@pytest.mark.asyncio
@patch("bot.callbacks.writer.get_processed_message_text", new_callable=AsyncMock)
async def test_writer_callback_error_keeps_message_answer(mock_get_processed_message_text):
    mock_get_processed_message_text.return_value = (None, "something went wrong")

    message = Mock(spec=Message)
    message.reply = AsyncMock()
    message.answer = AsyncMock()

    await writer_callback(message, Mock(spec=CommandObject))

    message.answer.assert_called_once_with("something went wrong")
    message.reply.assert_not_called()
