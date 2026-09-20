from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

from aiogram.types import Message

from bot.callbacks.translate import generate_translation_callback
from bot.core.message_response import MessageResponse


@patch.object(MessageResponse, "reply", new_callable=AsyncMock)
@patch("bot.callbacks.translate.translate", new_callable=AsyncMock)
@patch("bot.callbacks.translate.get_processed_message_text", new_callable=AsyncMock)
async def test_translation_callback_accepts_message_only(mock_processed_text, mock_translate, mock_reply):
    mock_processed_text.return_value = ("Hello", None)
    mock_translate.return_value = MessageResponse(content="こんにちは")
    message = Mock(spec=Message)

    callback = generate_translation_callback("日本語")
    await callback(message)

    mock_translate.assert_awaited_once_with("Hello", lang="日本語")
    mock_reply.assert_awaited_once_with(message)
