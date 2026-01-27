from unittest.mock import Mock

import pytest

from bot.bot import get_bot_token
from bot.bot import get_chat_filter
from bot.settings import settings


def test_get_bot_token_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful token retrieval"""
    monkeypatch.setattr(settings, "bot_token", "test_token_123")
    token = get_bot_token()
    assert token == "test_token_123"


def test_get_bot_token_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test error when BOT_TOKEN is not set"""
    monkeypatch.setattr(settings, "bot_token", "")
    with pytest.raises(ValueError, match="BOT_TOKEN is not set"):
        get_bot_token()


def test_get_bot_token_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test error when BOT_TOKEN is empty"""
    monkeypatch.setattr(settings, "bot_token", "")
    with pytest.raises(ValueError, match="BOT_TOKEN is not set"):
        get_bot_token()


def test_get_chat_filter_no_whitelist(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test chat filter when no whitelist is specified - allows all"""
    monkeypatch.setattr(settings, "bot_whitelist", None)
    chat_filter = get_chat_filter()
    # Should allow any message
    mock_message = Mock()
    mock_message.chat.id = 12345
    assert chat_filter(mock_message) is True


def test_get_chat_filter_empty_whitelist(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test chat filter when whitelist is empty - allows all"""
    monkeypatch.setattr(settings, "bot_whitelist", "")
    chat_filter = get_chat_filter()
    # Should allow any message
    mock_message = Mock()
    mock_message.chat.id = 12345
    assert chat_filter(mock_message) is True


def test_get_chat_filter_single_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test chat filter with single chat ID"""
    monkeypatch.setattr(settings, "bot_whitelist", "123456789")
    chat_filter = get_chat_filter()
    # Should allow whitelisted chat
    mock_message = Mock()
    mock_message.chat.id = 123456789
    assert chat_filter(mock_message) is True
    # Should reject non-whitelisted chat
    mock_message.chat.id = 999999999
    assert chat_filter(mock_message) is False


def test_get_chat_filter_multiple_chats(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test chat filter with multiple chat IDs"""
    monkeypatch.setattr(settings, "bot_whitelist", "123456789,987654321")
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


def test_get_chat_filter_with_spaces(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test chat filter with spaces in whitelist"""
    monkeypatch.setattr(settings, "bot_whitelist", "123456789, 987654321, 555666777")
    chat_filter = get_chat_filter()
    # Should allow all whitelisted chats
    mock_message = Mock()
    for chat_id in [123456789, 987654321, 555666777]:
        mock_message.chat.id = chat_id
        assert chat_filter(mock_message) is True
    # Should reject non-whitelisted chat
    mock_message.chat.id = 111111111
    assert chat_filter(mock_message) is False


def test_get_chat_filter_invalid_chat_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test error handling for invalid chat IDs"""
    monkeypatch.setattr(settings, "bot_whitelist", "invalid_id")
    with pytest.raises(ValueError):
        get_chat_filter()
