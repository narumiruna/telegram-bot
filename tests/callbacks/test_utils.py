from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from aiogram.types import Chat
from aiogram.types import Message
from aiogram.types import User

from bot.callbacks.utils import get_message_key
from bot.callbacks.utils import get_message_text
from bot.callbacks.utils import get_processed_message_text
from bot.callbacks.utils import get_user_display_name
from bot.callbacks.utils import safe_callback
from bot.callbacks.utils import strip_command


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("/sum 1 2 3", "1 2 3"),
        ("/start", ""),
        ("hello", "hello"),
        ("/command with multiple words", "with multiple words"),
        ("/", ""),
        ("/cmd", ""),
        ("/cmd ", ""),
        ("/cmd  multiple  spaces", " multiple  spaces"),
    ],
)
def test_strip_command(text, expected):
    assert strip_command(text) == expected


class TestGetUserDisplayName:
    def test_get_user_display_name_with_username(self):
        user = User(id=123, is_bot=False, first_name="なるみ", username="narumi")
        message = Mock(spec=Message)
        message.from_user = user

        result = get_user_display_name(message)
        assert result == "なるみ(narumi)"

    def test_get_user_display_name_without_username(self):
        user = User(id=123, is_bot=False, first_name="なるみ")
        message = Mock(spec=Message)
        message.from_user = user

        result = get_user_display_name(message)
        assert result == "なるみ"

    def test_get_user_display_name_no_user(self):
        message = Mock(spec=Message)
        message.from_user = None

        result = get_user_display_name(message)
        assert result is None


class TestGetMessageText:
    def setup_method(self):
        self.user = User(id=123, is_bot=False, first_name="TestUser", username="testuser")
        self.chat = Chat(id=456, type="private")

    def test_get_message_text_simple(self):
        message = Mock(spec=Message)
        message.text = "Hello world"
        message.caption = None
        message.from_user = self.user
        message.reply_to_message = None

        result = get_message_text(message)
        assert result == "Hello world"

    def test_get_message_text_with_command(self):
        message = Mock(spec=Message)
        message.text = "/translate Hello world"
        message.caption = None
        message.from_user = self.user
        message.reply_to_message = None

        result = get_message_text(message)
        assert result == "Hello world"

    def test_get_message_text_with_user_name(self):
        message = Mock(spec=Message)
        message.text = "Hello world"
        message.caption = None
        message.from_user = self.user
        message.reply_to_message = None

        result = get_message_text(message, include_user_name=True)
        assert result == "TestUser(testuser): Hello world"

    def test_get_message_text_with_reply(self):
        reply_message = Mock(spec=Message)
        reply_message.text = "Original message"
        reply_message.caption = None
        reply_message.from_user = self.user
        reply_message.reply_to_message = None

        message = Mock(spec=Message)
        message.text = "Reply message"
        message.caption = None
        message.from_user = self.user
        message.reply_to_message = reply_message

        result = get_message_text(message)
        assert result == "Original message\n\nReply message"

    def test_get_message_text_empty(self):
        message = Mock(spec=Message)
        message.text = None
        message.caption = None
        message.from_user = self.user
        message.reply_to_message = None

        result = get_message_text(message)
        assert result == ""


class TestGetMessageKey:
    def test_get_message_key(self):
        message = Mock(spec=Message)
        message.message_id = 123
        message.chat = Mock()
        message.chat.id = 456

        result = get_message_key(message)
        assert result == "123:456"


class TestGetProcessedMessageText:
    def setup_method(self):
        self.user = User(id=123, is_bot=False, first_name="TestUser", username="testuser")
        self.chat = Chat(id=456, type="private")

    @pytest.mark.asyncio
    async def test_no_message_text(self):
        message = Mock(spec=Message)
        message.text = ""
        message.caption = None
        message.from_user = self.user
        message.reply_to_message = None

        text, error = await get_processed_message_text(message, require_url=False)
        assert text is None
        assert error is None

    @pytest.mark.asyncio
    @patch("bot.callbacks.utils.parse_urls")
    async def test_require_url_but_no_url(self, mock_parse_urls):
        mock_parse_urls.return_value = []

        message = Mock(spec=Message)
        message.text = "No URL here"
        message.caption = None
        message.from_user = self.user
        message.reply_to_message = None

        text, error = await get_processed_message_text(message, require_url=True)
        assert text is None
        assert error is None

    @pytest.mark.asyncio
    @patch("bot.callbacks.utils.parse_urls")
    async def test_no_url_returns_original_text(self, mock_parse_urls):
        mock_parse_urls.return_value = []

        message = Mock(spec=Message)
        message.text = "No URL here"
        message.caption = None
        message.from_user = self.user
        message.reply_to_message = None

        text, error = await get_processed_message_text(message, require_url=False)
        assert text == "No URL here"
        assert error is None

    @pytest.mark.asyncio
    @patch("bot.callbacks.utils.load_url")
    @patch("bot.callbacks.utils.parse_urls")
    async def test_url_loading_success(self, mock_parse_urls, mock_load_url):
        mock_parse_urls.return_value = ["https://example.com"]
        mock_load_url.return_value = "Content from URL"

        message = Mock(spec=Message)
        message.text = "https://example.com"
        message.caption = None
        message.from_user = self.user
        message.reply_to_message = None

        text, error = await get_processed_message_text(message, require_url=False)
        assert text == "Content from URL"
        assert error is None
        mock_load_url.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    @patch("bot.callbacks.utils.load_url")
    @patch("bot.callbacks.utils.parse_urls")
    async def test_url_loading_failure(self, mock_parse_urls, mock_load_url):
        mock_parse_urls.return_value = ["https://example.com"]
        mock_load_url.side_effect = Exception("Connection error")

        message = Mock(spec=Message)
        message.text = "https://example.com"
        message.caption = None
        message.from_user = self.user
        message.reply_to_message = None

        text, error = await get_processed_message_text(message, require_url=False)
        assert text is None
        assert error == "Failed to load URL(s): https://example.com"

    @pytest.mark.asyncio
    @patch("bot.callbacks.utils.load_url")
    @patch("bot.callbacks.utils.parse_urls")
    async def test_require_url_with_url_success(self, mock_parse_urls, mock_load_url):
        mock_parse_urls.return_value = ["https://example.com"]
        mock_load_url.return_value = "Content from URL"

        message = Mock(spec=Message)
        message.text = "https://example.com"
        message.caption = None
        message.from_user = self.user
        message.reply_to_message = None

        text, error = await get_processed_message_text(message, require_url=True)
        assert text == "Content from URL"
        assert error is None
        mock_load_url.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    @patch("bot.callbacks.utils.load_url")
    @patch("bot.callbacks.utils.parse_urls")
    async def test_multiple_urls_loading_success(self, mock_parse_urls, mock_load_url):
        mock_parse_urls.return_value = ["https://example1.com", "https://example2.com"]
        mock_load_url.side_effect = ["Content from URL 1", "Content from URL 2"]

        message = Mock(spec=Message)
        message.text = "Check https://example1.com and https://example2.com"
        message.caption = None
        message.from_user = self.user
        message.reply_to_message = None

        text, error = await get_processed_message_text(message, require_url=False)
        assert text == "Content from URL 1\n\n---\n\nContent from URL 2"
        assert error is None
        assert mock_load_url.call_count == 2

    @pytest.mark.asyncio
    @patch("bot.callbacks.utils.load_url")
    @patch("bot.callbacks.utils.parse_urls")
    async def test_multiple_urls_one_fails(self, mock_parse_urls, mock_load_url):
        mock_parse_urls.return_value = ["https://example1.com", "https://example2.com"]
        mock_load_url.side_effect = Exception("Connection error")

        message = Mock(spec=Message)
        message.text = "Check https://example1.com and https://example2.com"
        message.caption = None
        message.from_user = self.user
        message.reply_to_message = None

        text, error = await get_processed_message_text(message, require_url=False)
        assert text is None
        assert error == "Failed to load URL(s): https://example1.com, https://example2.com"

    @pytest.mark.asyncio
    @patch("bot.callbacks.utils.load_url")
    @patch("bot.callbacks.utils.parse_urls")
    async def test_multiple_urls_require_url(self, mock_parse_urls, mock_load_url):
        mock_parse_urls.return_value = ["https://example1.com", "https://example2.com", "https://example3.com"]
        mock_load_url.side_effect = ["Content 1", "Content 2", "Content 3"]

        message = Mock(spec=Message)
        message.text = "Three URLs: https://example1.com https://example2.com https://example3.com"
        message.caption = None
        message.from_user = self.user
        message.reply_to_message = None

        text, error = await get_processed_message_text(message, require_url=True)
        assert text == "Content 1\n\n---\n\nContent 2\n\n---\n\nContent 3"
        assert error is None
        assert mock_load_url.call_count == 3


class TestSafeCallback:
    def setup_method(self):
        self.user = User(id=123, is_bot=False, first_name="TestUser", username="testuser")
        self.chat = Chat(id=456, type="private")

    @pytest.mark.asyncio
    async def test_normal_execution(self):
        """Test that decorator doesn't interfere with normal execution"""
        mock_message = Mock(spec=Message)

        @safe_callback
        async def test_callback(message):
            return "success"

        result = await test_callback(mock_message)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are caught, logged, and user is notified"""
        mock_message = Mock(spec=Message)
        mock_message.answer = AsyncMock()

        @safe_callback
        async def test_callback(message):
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await test_callback(mock_message)

        # Verify user was notified
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "抱歉" in call_args
        assert "錯誤" in call_args

    @pytest.mark.asyncio
    async def test_answer_fails(self):
        """Test handling when answer itself fails"""
        mock_message = Mock(spec=Message)
        mock_message.answer = AsyncMock(side_effect=Exception("Reply failed"))

        @safe_callback
        async def test_callback(message):
            raise ValueError("Test error")

        # Should still raise the original exception
        with pytest.raises(ValueError):
            await test_callback(mock_message)

        # Verify answer was attempted
        mock_message.answer.assert_called_once()
