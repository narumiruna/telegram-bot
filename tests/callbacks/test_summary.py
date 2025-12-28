from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from telegram import Chat
from telegram import Message
from telegram import Update
from telegram import User

from bot.callbacks.summary import summarize_callback


class TestSummarizeCallback:
    def setup_method(self):
        self.user = User(id=123, is_bot=False, first_name="TestUser", username="testuser")
        self.chat = Chat(id=456, type="private")
        self.context = Mock()

    @pytest.mark.asyncio
    async def test_summarize_callback_no_message(self):
        update = Mock(spec=Update)
        update.message = None

        result = await summarize_callback(update, self.context)
        assert result is None

    @pytest.mark.asyncio
    async def test_summarize_callback_empty_message(self):
        message = Mock(spec=Message)
        message.text = ""
        message.from_user = self.user
        message.reply_to_message = None

        update = Mock(spec=Update)
        update.message = message

        result = await summarize_callback(update, self.context)
        assert result is None

    @pytest.mark.asyncio
    @patch("bot.callbacks.summary.get_processed_message_text")
    async def test_summarize_callback_no_url(self, mock_get_processed):
        mock_get_processed.return_value = (None, None)

        message = Mock(spec=Message)
        message.text = "This message has no URL"
        message.from_user = self.user
        message.reply_to_message = None

        update = Mock(spec=Update)
        update.message = message

        result = await summarize_callback(update, self.context)
        assert result is None
        mock_get_processed.assert_called_once_with(message, require_url=True)

    @pytest.mark.asyncio
    @patch("bot.callbacks.summary.chains.summarize")
    @patch("bot.callbacks.summary.get_processed_message_text")
    async def test_summarize_callback_success(self, mock_get_processed, mock_summarize):
        from bot.presentation import MessageResponse

        mock_get_processed.return_value = ("Content from URL to summarize", None)

        # Mock MessageResponse
        mock_response = Mock(spec=MessageResponse)
        mock_response.content = "This is a summary of the content"
        mock_response.send = AsyncMock()
        mock_summarize.return_value = mock_response

        message = Mock(spec=Message)
        message.text = "Summarize this: https://example.com"
        message.from_user = self.user
        message.reply_to_message = None
        message.reply_text = AsyncMock()

        update = Mock(spec=Update)
        update.message = message

        await summarize_callback(update, self.context)

        mock_get_processed.assert_called_once_with(message, require_url=True)
        mock_summarize.assert_called_once_with("Content from URL to summarize")
        mock_response.send.assert_called_once_with(message)

    @pytest.mark.asyncio
    @patch("bot.callbacks.summary.get_processed_message_text")
    async def test_summarize_callback_url_load_error(self, mock_get_processed):
        mock_get_processed.return_value = (None, "Failed to load URL: https://example.com")

        message = Mock(spec=Message)
        message.text = "Summarize this: https://example.com"
        message.from_user = self.user
        message.reply_to_message = None
        message.reply_text = AsyncMock()

        update = Mock(spec=Update)
        update.message = message

        await summarize_callback(update, self.context)

        mock_get_processed.assert_called_once_with(message, require_url=True)
        message.reply_text.assert_called_once_with("Failed to load URL: https://example.com")
