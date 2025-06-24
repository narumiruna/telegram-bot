from unittest.mock import Mock

import pytest
from telegram import Chat
from telegram import Message
from telegram import User

from bot.callbacks.utils import get_message_key
from bot.callbacks.utils import get_message_text
from bot.callbacks.utils import get_user_display_name
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
        message = Message(message_id=1, date=None, chat=self.chat, from_user=self.user, text="Hello world")

        result = get_message_text(message)
        assert result == "Hello world"

    def test_get_message_text_with_command(self):
        message = Message(message_id=1, date=None, chat=self.chat, from_user=self.user, text="/translate Hello world")

        result = get_message_text(message)
        assert result == "Hello world"

    def test_get_message_text_with_user_name(self):
        message = Message(message_id=1, date=None, chat=self.chat, from_user=self.user, text="Hello world")

        result = get_message_text(message, include_user_name=True)
        assert result == "TestUser(testuser): Hello world"

    def test_get_message_text_with_reply(self):
        reply_message = Message(message_id=1, date=None, chat=self.chat, from_user=self.user, text="Original message")

        message = Message(
            message_id=2,
            date=None,
            chat=self.chat,
            from_user=self.user,
            text="Reply message",
            reply_to_message=reply_message,
        )

        result = get_message_text(message)
        assert result == "Original message\n\nReply message"

    def test_get_message_text_empty(self):
        message = Message(message_id=1, date=None, chat=self.chat, from_user=self.user, text=None)

        result = get_message_text(message)
        assert result == ""


class TestGetMessageKey:
    def test_get_message_key(self):
        chat = Chat(id=456, type="private")
        message = Message(message_id=123, date=None, chat=chat)

        result = get_message_key(message)
        assert result == "123:456"
