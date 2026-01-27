import os
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from bot.bot import get_bot_token
from bot.bot import get_chat_filter


def test_get_bot_token_success() -> None:
    """Test successful token retrieval"""
    with patch.dict(os.environ, {"BOT_TOKEN": "test_token_123"}):
        token = get_bot_token()
        assert token == "test_token_123"


def test_get_bot_token_missing() -> None:
    """Test error when BOT_TOKEN is not set"""
    with (
        patch.dict(os.environ, {}, clear=True),
        pytest.raises(ValueError, match="BOT_TOKEN is not set"),
    ):
        get_bot_token()


def test_get_bot_token_empty() -> None:
    """Test error when BOT_TOKEN is empty"""
    with (
        patch.dict(os.environ, {"BOT_TOKEN": ""}),
        pytest.raises(ValueError, match="BOT_TOKEN is not set"),
    ):
        get_bot_token()


def test_get_chat_filter_no_whitelist() -> None:
    """Test chat filter when no whitelist is specified - allows all"""
    with patch.dict(os.environ, {}, clear=True):
        chat_filter = get_chat_filter()
        # Should allow any message
        mock_message = Mock()
        mock_message.chat.id = 12345
        assert chat_filter(mock_message) is True


def test_get_chat_filter_empty_whitelist() -> None:
    """Test chat filter when whitelist is empty - allows all"""
    with patch.dict(os.environ, {"BOT_WHITELIST": ""}):
        chat_filter = get_chat_filter()
        # Should allow any message
        mock_message = Mock()
        mock_message.chat.id = 12345
        assert chat_filter(mock_message) is True


def test_get_chat_filter_single_chat() -> None:
    """Test chat filter with single chat ID"""
    with patch.dict(os.environ, {"BOT_WHITELIST": "123456789"}):
        chat_filter = get_chat_filter()
        # Should allow whitelisted chat
        mock_message = Mock()
        mock_message.chat.id = 123456789
        assert chat_filter(mock_message) is True
        # Should reject non-whitelisted chat
        mock_message.chat.id = 999999999
        assert chat_filter(mock_message) is False


def test_get_chat_filter_multiple_chats() -> None:
    """Test chat filter with multiple chat IDs"""
    with patch.dict(os.environ, {"BOT_WHITELIST": "123456789,987654321"}):
        chat_filter = get_chat_filter()
        # Should allow both whitelisted chats
        mock_message = Mock()
        mock_message.chat.id = 123456789
        assert chat_filter(mock_message) is True
        mock_message.chat.id = 987654321
        assert chat_filter(mock_message) is True
        # Should reject non-whitelisted chat
        mock_message.chat.id = 111111111
        assert chat_filter(mock_message) is False


def test_get_chat_filter_with_spaces() -> None:
    """Test chat filter with spaces in whitelist"""
    with patch.dict(os.environ, {"BOT_WHITELIST": "123456789, 987654321, 555666777"}):
        chat_filter = get_chat_filter()
        # Should allow all whitelisted chats
        mock_message = Mock()
        for chat_id in [123456789, 987654321, 555666777]:
            mock_message.chat.id = chat_id
            assert chat_filter(mock_message) is True
        # Should reject non-whitelisted chat
        mock_message.chat.id = 111111111
        assert chat_filter(mock_message) is False


def test_get_chat_filter_invalid_chat_id() -> None:
    """Test error handling for invalid chat IDs"""
    with (
        patch.dict(os.environ, {"BOT_WHITELIST": "invalid_id"}),
        pytest.raises(ValueError),
    ):
        get_chat_filter()
