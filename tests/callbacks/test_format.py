from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from telegram import Chat
from telegram import Message
from telegram import Update
from telegram import User

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
        mock_result = Mock()
        mock_result.title = "Test Title"
        mock_result.__str__ = Mock(return_value="Formatted content")
        mock_format.return_value = mock_result

        message = Mock(spec=Message)
        message.text = "Test message to format"
        message.from_user = self.user
        message.reply_to_message = None
        message.reply_text = AsyncMock()

        update = Mock(spec=Update)
        update.message = message

        await format_callback(update, self.context)

        mock_format.assert_called_once_with("Test message to format")
        message.reply_text.assert_called_once_with("Formatted content")

    @pytest.mark.asyncio
    @patch("bot.callbacks.format.chains.format")
    @patch("bot.callbacks.format.get_processed_message_text")
    async def test_format_callback_with_url(self, mock_get_processed, mock_format):
        mock_get_processed.return_value = ("Content from URL", None)

        mock_result = Mock()
        mock_result.title = "Test Title"
        mock_result.__str__ = Mock(return_value="Formatted URL content")
        mock_format.return_value = mock_result

        message = Mock(spec=Message)
        message.text = "Check this URL: https://example.com"
        message.from_user = self.user
        message.reply_to_message = None
        message.reply_text = AsyncMock()

        update = Mock(spec=Update)
        update.message = message

        await format_callback(update, self.context)

        mock_get_processed.assert_called_once_with(message, require_url=False)
        mock_format.assert_called_once_with("Content from URL")
        message.reply_text.assert_called_once_with("Formatted URL content")

    @pytest.mark.asyncio
    @patch("bot.callbacks.format.chains.format")
    @patch("bot.callbacks.format.async_create_page")
    async def test_format_callback_long_content(self, mock_async_create_page, mock_format):
        long_content = "x" * 1500  # Longer than MAX_LENGTH (1000)
        mock_result = Mock()
        mock_result.title = "Long Title"
        mock_result.__str__ = Mock(return_value=long_content)
        mock_format.return_value = mock_result

        mock_async_create_page.return_value = "HTML page content"

        message = Mock(spec=Message)
        message.text = "Long message to format"
        message.from_user = self.user
        message.reply_to_message = None
        message.reply_text = AsyncMock()

        update = Mock(spec=Update)
        update.message = message

        await format_callback(update, self.context)

        mock_format.assert_called_once_with("Long message to format")
        mock_async_create_page.assert_called_once_with(
            title="Long Title", html_content=long_content.replace("\n", "<br>")
        )
        message.reply_text.assert_called_once_with("HTML page content")
