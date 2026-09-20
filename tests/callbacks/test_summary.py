from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

from aiogram.types import Message

from bot.callbacks.summary import summarize_callback
from bot.core.message_response import MessageResponse


@patch.object(MessageResponse, "reply", new_callable=AsyncMock)
@patch("bot.callbacks.summary.summarize", new_callable=AsyncMock)
@patch("bot.callbacks.summary.get_processed_message_text", new_callable=AsyncMock)
async def test_summarize_callback_accepts_message_only(mock_processed_text, mock_summarize, mock_reply):
    mock_processed_text.return_value = ("https://example.com", None)
    response = MessageResponse(content="摘要內容")
    mock_summarize.return_value = response
    message = Mock(spec=Message)

    await summarize_callback(message)

    mock_summarize.assert_awaited_once_with("https://example.com")
    assert response.title == "摘要"
    mock_reply.assert_awaited_once_with(message)
