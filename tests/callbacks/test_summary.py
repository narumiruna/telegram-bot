from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from telegram import Chat
from telegram import Message
from telegram import Update
from telegram import User
from telegram.constants import ParseMode

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
    @patch("bot.callbacks.summary.parse_url")
    async def test_summarize_callback_no_url(self, mock_parse_url):
        mock_parse_url.return_value = None

        message = Mock(spec=Message)
        message.text = "This message has no URL"
        message.from_user = self.user
        message.reply_to_message = None

        update = Mock(spec=Update)
        update.message = message

        result = await summarize_callback(update, self.context)
        assert result is None
        mock_parse_url.assert_called_once_with("This message has no URL")

    @pytest.mark.asyncio
    @patch("bot.callbacks.summary.chains.summarize")
    @patch("bot.callbacks.summary.async_load_url")
    @patch("bot.callbacks.summary.parse_url")
    async def test_summarize_callback_success(self, mock_parse_url, mock_load_url, mock_summarize):
        mock_parse_url.return_value = "https://example.com"
        mock_load_url.return_value = "Content from URL to summarize"
        mock_summarize.return_value = "This is a summary of the content"

        message = Mock(spec=Message)
        message.text = "Summarize this: https://example.com"
        message.from_user = self.user
        message.reply_to_message = None
        message.reply_text = AsyncMock()

        update = Mock(spec=Update)
        update.message = message

        await summarize_callback(update, self.context)

        mock_parse_url.assert_called_once_with("Summarize this: https://example.com")
        mock_load_url.assert_called_once_with("https://example.com")
        mock_summarize.assert_called_once_with("Content from URL to summarize")
        message.reply_text.assert_called_once_with(
            "This is a summary of the content", parse_mode=ParseMode.HTML, disable_web_page_preview=True
        )

    @pytest.mark.asyncio
    @patch("bot.callbacks.summary.async_load_url")
    @patch("bot.callbacks.summary.parse_url")
    async def test_summarize_callback_url_load_error(self, mock_parse_url, mock_load_url):
        mock_parse_url.return_value = "https://example.com"
        mock_load_url.side_effect = Exception("Connection error")

        message = Mock(spec=Message)
        message.text = "Summarize this: https://example.com"
        message.from_user = self.user
        message.reply_to_message = None
        message.reply_text = AsyncMock()

        update = Mock(spec=Update)
        update.message = message

        await summarize_callback(update, self.context)

        mock_parse_url.assert_called_once_with("Summarize this: https://example.com")
        mock_load_url.assert_called_once_with("https://example.com")
        message.reply_text.assert_called_once_with("Failed to load URL: https://example.com")
