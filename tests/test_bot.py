from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from bot.bot import get_chat_filter
from bot.bot import run_bot
from bot.settings import settings


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


@pytest.mark.parametrize(("reply_enabled", "expected_registrations"), [(False, 0), (True, 1)])
async def test_run_bot_registers_reply_handler_only_when_enabled(monkeypatch, reply_enabled, expected_registrations):
    agent = Mock()

    @asynccontextmanager
    async def chat_agent_context():
        yield agent

    bot = Mock()
    bot.session.close = AsyncMock()
    dispatcher = Mock()
    dispatcher.start_polling = AsyncMock()
    dispatcher.stop_polling = AsyncMock()
    router = Mock()
    router.message.register = Mock()
    router.errors.register = Mock()
    shutdown = Mock()
    shutdown.wait = AsyncMock()
    shutdown.cancel_tasks = AsyncMock()

    monkeypatch.setattr(settings, "bot_token", "123456:TEST_TOKEN")
    monkeypatch.setattr(settings, "agent_reply_enabled", reply_enabled)

    with (
        patch("bot.bot.build_chat_agent", return_value=chat_agent_context()),
        patch("bot.bot.Bot", return_value=bot),
        patch("bot.bot.Dispatcher", return_value=dispatcher),
        patch("bot.bot.Router", return_value=router),
        patch("bot.bot.ShutdownManager", return_value=shutdown),
    ):
        await run_bot()

    registered_callbacks = [call.args[0] for call in router.message.register.call_args_list]
    reply_registrations = [callback for callback in registered_callbacks if callback.__name__ == "handle_reply"]
    assert len(reply_registrations) == expected_registrations
