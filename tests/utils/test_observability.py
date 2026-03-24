import logging

from bot.settings import settings
from bot.utils.observability import bind_log_context
from bot.utils.observability import clear_log_context
from bot.utils.observability import configure_logging
from bot.utils.observability import get_log_context


def test_configure_logging_uses_configured_log_level(monkeypatch) -> None:
    monkeypatch.setattr(settings, "log_level", "DEBUG")
    monkeypatch.setattr(settings, "log_json", False)
    monkeypatch.setattr(settings, "logfire_token", None)

    configure_logging()

    assert logging.getLogger().level == logging.DEBUG


def test_log_context_binding_and_clearing() -> None:
    assert get_log_context() == {}

    token = bind_log_context(chat_id=123, handler="handle_command")
    assert get_log_context()["chat_id"] == "123"
    assert get_log_context()["handler"] == "handle_command"

    clear_log_context(token)
    assert get_log_context() == {}
