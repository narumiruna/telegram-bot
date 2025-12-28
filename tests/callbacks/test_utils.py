import datetime
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from telegram import Chat
from telegram import Message
from telegram import User

from bot.callbacks.utils import get_message_key
from bot.callbacks.utils import get_message_text
from bot.callbacks.utils import get_processed_message_text
from bot.callbacks.utils import get_user_display_name
from bot.callbacks.utils import safe_callback
from bot.callbacks.utils import strip_command


@pytest.mark.parametrize(
    "text, expected",
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
        message = Message(
            message_id=1, date=datetime.datetime.now(), chat=self.chat, from_user=self.user, text="Hello world"
        )

        result = get_message_text(message)
        assert result == "Hello world"

    def test_get_message_text_with_command(self):
        message = Message(
            message_id=1,
            date=datetime.datetime.now(),
            chat=self.chat,
            from_user=self.user,
            text="/translate Hello world",
        )

        result = get_message_text(message)
        assert result == "Hello world"

    def test_get_message_text_with_user_name(self):
        message = Message(
            message_id=1, date=datetime.datetime.now(), chat=self.chat, from_user=self.user, text="Hello world"
        )

        result = get_message_text(message, include_user_name=True)
        assert result == "TestUser(testuser): Hello world"

    def test_get_message_text_with_reply(self):
        reply_message = Message(
            message_id=1, date=datetime.datetime.now(), chat=self.chat, from_user=self.user, text="Original message"
        )

        message = Message(
            message_id=2,
            date=datetime.datetime.now(),
            chat=self.chat,
            from_user=self.user,
            text="Reply message",
            reply_to_message=reply_message,
        )

        result = get_message_text(message)
        assert result == "Original message\n\nReply message"

    def test_get_message_text_empty(self):
        message = Message(message_id=1, date=datetime.datetime.now(), chat=self.chat, from_user=self.user, text=None)

        result = get_message_text(message)
        assert result == ""


class TestGetMessageKey:
    def test_get_message_key(self):
        chat = Chat(id=456, type="private")

        message = Message(message_id=123, date=datetime.datetime.now(), chat=chat)

        result = get_message_key(message)
        assert result == "123:456"


class TestGetProcessedMessageText:
    def setup_method(self):
        self.user = User(id=123, is_bot=False, first_name="TestUser", username="testuser")
        self.chat = Chat(id=456, type="private")

    @pytest.mark.asyncio
    async def test_no_message_text(self):
        message = Message(message_id=1, date=datetime.datetime.now(), chat=self.chat, from_user=self.user, text="")

        text, error = await get_processed_message_text(message, require_url=False)
        assert text is None
        assert error is None

    @pytest.mark.asyncio
    @patch("bot.callbacks.utils.parse_url")
    async def test_require_url_but_no_url(self, mock_parse_url):
        mock_parse_url.return_value = ""

        message = Message(
            message_id=1, date=datetime.datetime.now(), chat=self.chat, from_user=self.user, text="No URL here"
        )

        text, error = await get_processed_message_text(message, require_url=True)
        assert text is None
        assert error is None

    @pytest.mark.asyncio
    @patch("bot.callbacks.utils.parse_url")
    async def test_no_url_returns_original_text(self, mock_parse_url):
        mock_parse_url.return_value = ""

        message = Message(
            message_id=1, date=datetime.datetime.now(), chat=self.chat, from_user=self.user, text="No URL here"
        )

        text, error = await get_processed_message_text(message, require_url=False)
        assert text == "No URL here"
        assert error is None

    @pytest.mark.asyncio
    @patch("bot.callbacks.utils.async_load_url")
    @patch("bot.callbacks.utils.parse_url")
    async def test_url_loading_success(self, mock_parse_url, mock_load_url):
        mock_parse_url.return_value = "https://example.com"
        mock_load_url.return_value = "Content from URL"

        message = Message(
            message_id=1, date=datetime.datetime.now(), chat=self.chat, from_user=self.user, text="https://example.com"
        )

        text, error = await get_processed_message_text(message, require_url=False)
        assert text == "Content from URL"
        assert error is None
        mock_load_url.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    @patch("bot.callbacks.utils.async_load_url")
    @patch("bot.callbacks.utils.parse_url")
    async def test_url_loading_failure(self, mock_parse_url, mock_load_url):
        mock_parse_url.return_value = "https://example.com"
        mock_load_url.side_effect = Exception("Connection error")

        message = Message(
            message_id=1, date=datetime.datetime.now(), chat=self.chat, from_user=self.user, text="https://example.com"
        )

        text, error = await get_processed_message_text(message, require_url=False)
        assert text is None
        assert error == "Failed to load URL: https://example.com"

    @pytest.mark.asyncio
    @patch("bot.callbacks.utils.async_load_url")
    @patch("bot.callbacks.utils.parse_url")
    async def test_require_url_with_url_success(self, mock_parse_url, mock_load_url):
        mock_parse_url.return_value = "https://example.com"
        mock_load_url.return_value = "Content from URL"

        message = Message(
            message_id=1, date=datetime.datetime.now(), chat=self.chat, from_user=self.user, text="https://example.com"
        )

        text, error = await get_processed_message_text(message, require_url=True)
        assert text == "Content from URL"
        assert error is None
        mock_load_url.assert_called_once_with("https://example.com")


class TestSafeCallback:
    def setup_method(self):
        self.user = User(id=123, is_bot=False, first_name="TestUser", username="testuser")
        self.chat = Chat(id=456, type="private")

    @pytest.mark.asyncio
    async def test_normal_execution(self):
        """Test that decorator doesn't interfere with normal execution"""
        mock_message = Mock(spec=Message)
        mock_update = Mock()
        mock_update.message = mock_message
        mock_context = Mock()

        @safe_callback
        async def test_callback(update, context):
            return "success"

        result = await test_callback(mock_update, mock_context)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are caught, logged, and user is notified"""
        mock_message = Mock(spec=Message)
        mock_update = Mock()
        mock_update.message = mock_message
        mock_context = Mock()

        @safe_callback
        async def test_callback(update, context):
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await test_callback(mock_update, mock_context)

        # Verify user was notified
        mock_message.reply_text.assert_called_once()
        call_args = mock_message.reply_text.call_args[0][0]
        assert "抱歉" in call_args
        assert "錯誤" in call_args

    @pytest.mark.asyncio
    async def test_no_message_in_update(self):
        """Test handling when update has no message"""
        mock_update = Mock()
        mock_update.message = None
        mock_context = Mock()

        @safe_callback
        async def test_callback(update, context):
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await test_callback(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_reply_text_fails(self):
        """Test handling when reply_text itself fails"""
        mock_message = Mock(spec=Message)
        mock_message.reply_text.side_effect = Exception("Reply failed")
        mock_update = Mock()
        mock_update.message = mock_message
        mock_context = Mock()

        @safe_callback
        async def test_callback(update, context):
            raise ValueError("Test error")

        # Should still raise the original exception
        with pytest.raises(ValueError):
            await test_callback(mock_update, mock_context)

        # Verify reply_text was attempted
        mock_message.reply_text.assert_called_once()
