from unittest.mock import AsyncMock
from unittest.mock import Mock

import pytest

from bot.callbacks.error import error_callback
from bot.settings import settings
from bot.utils.observability import get_log_context


@pytest.mark.asyncio
async def test_error_callback_logs_exception_and_clears_context(caplog, monkeypatch) -> None:
    monkeypatch.setattr(settings, "developer_chat_id", None)
    bot = Mock()
    bot.send_message = AsyncMock()

    event = Mock()
    event.exception = ValueError("boom")
    event.update = Mock()
    event.update.update_id = 1234
    event.update.message = Mock()
    event.update.message.message_id = 88
    event.update.message.chat = Mock()
    event.update.message.chat.id = 456
    event.update.message.from_user = Mock()
    event.update.message.from_user.id = 789

    with caplog.at_level("ERROR"):
        await error_callback(event, bot)

    assert "Exception while handling an update." in caplog.text
    assert "ValueError: boom" in caplog.text
    assert get_log_context() == {}
