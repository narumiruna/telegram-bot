from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from aiogram.types import Chat
from aiogram.types import Message
from aiogram.types import Update
from aiogram.types import User

from bot.callbacks.format import format_callback


class TestFormatCallback:
    def setup_method(self):
        self.user = User(id=123, is_bot=False, first_name="TestUser", username="testuser")
        self.chat = Chat(id=456, type="private")
        self.context = Mock()

    @pytest.mark.asyncio
    async def test_format_callback_no_message(self):
        update = Mock(spec=Update)
        update.message = None

        result = await format_callback(update, self.context)
        assert result is None

    @pytest.mark.asyncio
    async def test_format_callback_empty_message(self):
        message = Mock(spec=Message)
        message.text = ""
        message.from_user = self.user
        message.reply_to_message = None

        update = Mock(spec=Update)
        update.message = message

        result = await format_callback(update, self.context)
        assert result is None

    @pytest.mark.asyncio
    @patch("bot.callbacks.format.chains.format")
    async def test_format_callback_simple_text(self, mock_format):
        # Mock Article with to_message_response() method
        mock_article = Mock()
        mock_response = Mock()
        mock_response.send = AsyncMock()
        mock_article.to_message_response.return_value = mock_response
        mock_format.return_value = mock_article

        message = Mock(spec=Message)
        message.text = "Test message to format"
        message.from_user = self.user
        message.reply_to_message = None
        message.answer = AsyncMock()

        update = Mock(spec=Update)
        update.message = message

        await format_callback(update, self.context)

        mock_format.assert_called_once_with("Test message to format")
        mock_response.send.assert_called_once_with(message)

    @pytest.mark.asyncio
    @patch("bot.callbacks.format.chains.format")
    @patch("bot.callbacks.format.get_processed_message_text")
    async def test_format_callback_with_url(self, mock_get_processed, mock_format):
        mock_get_processed.return_value = ("Content from URL", None)

        # Mock Article with to_message_response() method
        mock_article = Mock()
        mock_response = Mock()
        mock_response.send = AsyncMock()
        mock_article.to_message_response.return_value = mock_response
        mock_format.return_value = mock_article

        message = Mock(spec=Message)
        message.text = "Check this URL: https://example.com"
        message.from_user = self.user
        message.reply_to_message = None
        message.answer = AsyncMock()

        update = Mock(spec=Update)
        update.message = message

        await format_callback(update, self.context)

        mock_get_processed.assert_called_once_with(message, require_url=False)
        mock_format.assert_called_once_with("Content from URL")
        mock_response.send.assert_called_once_with(message)

    @pytest.mark.asyncio
    @patch("bot.callbacks.format.chains.format")
    async def test_format_callback_long_content(self, mock_format):
        # Mock Article with to_message_response() method
        mock_article = Mock()
        mock_response = Mock()
        mock_response.send = AsyncMock()
        mock_article.to_message_response.return_value = mock_response
        mock_format.return_value = mock_article

        message = Mock(spec=Message)
        message.text = "Short text"
        message.from_user = self.user
        message.reply_to_message = None
        message.answer = AsyncMock()

        update = Mock(spec=Update)
        update.message = message

        await format_callback(update, self.context)

        mock_format.assert_called_once()
        # MessageResponse.send() will handle Telegraph page creation internally
        mock_response.send.assert_called_once_with(message)
