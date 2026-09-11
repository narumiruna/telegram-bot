import logging
from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import httpx2
import pytest
from agents.exceptions import ModelTimeoutError
from aiogram import Bot
from aiogram.enums import ChatType
from aiogram.types import Chat
from aiogram.types import Message
from openai import APITimeoutError

from bot.agents.error import ErrorExplanation
from bot.callbacks.error import error_callback
from bot.settings import settings

BOT_TOKEN = "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"


def _make_event(error: Exception, update_event: object) -> Mock:
    event = Mock()
    event.exception = error
    event.update.event = update_event
    event.update.model_dump.return_value = {"update_id": 123}
    return event


def _make_message() -> Message:
    return Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=123, type=ChatType.PRIVATE),
        text="request",
    )


def _make_bot() -> Bot:
    return Bot(token=BOT_TOKEN)


def _make_error_with_traceback(message: str) -> RuntimeError:
    try:
        raise RuntimeError(message)
    except RuntimeError as error:
        return error


@patch.object(Bot, "send_message", new_callable=AsyncMock)
@patch.object(Message, "reply", new_callable=AsyncMock)
@patch("bot.callbacks.error.async_create_page", new_callable=AsyncMock)
@patch("bot.callbacks.error.explain_error", new_callable=AsyncMock)
async def test_error_callback_explains_error_to_user_and_administrator(
    mock_explain_error,
    mock_create_page,
    mock_reply,
    mock_send_message,
    monkeypatch,
):
    monkeypatch.setattr(settings, "developer_chat_id", "456")
    explanation = ErrorExplanation(
        user_message="外部服務暫時沒有回應，請稍後重送一次。",
        administrator_message="ReadTimeout；請檢查上游服務連線。",
    )
    mock_explain_error.return_value = explanation
    mock_create_page.return_value = "https://example.com/error"
    error = TimeoutError("upstream timeout")
    message = _make_message()
    event = _make_event(error, message)
    bot = _make_bot()

    await error_callback(event, bot)

    mock_explain_error.assert_awaited_once_with(error)
    mock_reply.assert_awaited_once_with(
        explanation.user_message,
        parse_mode=None,
        allow_sending_without_reply=True,
    )
    mock_create_page.assert_awaited_once()
    mock_send_message.assert_awaited_once_with(
        chat_id="456",
        text=("錯誤摘要：ReadTimeout；請檢查上游服務連線。\n\n診斷資料：https://example.com/error"),
    )


@patch.object(Bot, "send_message", new_callable=AsyncMock)
@patch.object(Message, "reply", new_callable=AsyncMock)
@patch("bot.callbacks.error.async_create_page", new_callable=AsyncMock)
@patch("bot.callbacks.error.explain_error", new_callable=AsyncMock)
async def test_error_callback_notifies_user_without_configured_administrator(
    mock_explain_error,
    mock_create_page,
    mock_reply,
    mock_send_message,
    monkeypatch,
):
    monkeypatch.setattr(settings, "developer_chat_id", None)
    explanation = ErrorExplanation(user_message="請先停止重試。", administrator_message="ValueError")
    mock_explain_error.return_value = explanation
    message = _make_message()
    event = _make_event(ValueError("bad input"), message)
    bot = _make_bot()

    await error_callback(event, bot)

    mock_reply.assert_awaited_once()
    mock_create_page.assert_not_awaited()
    mock_send_message.assert_not_awaited()


@patch.object(Bot, "send_message", new_callable=AsyncMock)
@patch("bot.callbacks.error.async_create_page", new_callable=AsyncMock)
@patch("bot.callbacks.error.explain_error", new_callable=AsyncMock)
async def test_error_callback_notifies_administrator_without_originating_message(
    mock_explain_error,
    mock_create_page,
    mock_send_message,
    monkeypatch,
):
    monkeypatch.setattr(settings, "developer_chat_id", "456")
    explanation = ErrorExplanation(user_message="請稍後重試。", administrator_message="背景工作失敗。")
    mock_explain_error.return_value = explanation
    mock_create_page.return_value = "https://example.com/error"
    event = _make_event(RuntimeError("background failure"), object())
    bot = _make_bot()

    await error_callback(event, bot)

    mock_send_message.assert_awaited_once()


@patch.object(Bot, "send_message", new_callable=AsyncMock)
@patch.object(Message, "reply", new_callable=AsyncMock)
@patch("bot.callbacks.error.explain_error", new_callable=AsyncMock)
async def test_error_callback_uses_error_derived_fallback_when_agent_fails(
    mock_explain_error,
    mock_reply,
    mock_send_message,
    monkeypatch,
):
    monkeypatch.setattr(settings, "developer_chat_id", None)
    mock_explain_error.side_effect = RuntimeError("model unavailable")
    message = _make_message()
    event = _make_event(ValueError("invalid input"), message)

    await error_callback(event, _make_bot())

    response = mock_reply.await_args.args[0]
    assert "處理資料時中止" in response
    assert "先不要重複傳送" in response
    assert "抱歉，處理您的請求時發生錯誤" not in response
    mock_send_message.assert_not_awaited()


@pytest.mark.parametrize(
    "error",
    [
        APITimeoutError(request=httpx2.Request("POST", "https://model.example.invalid")),
        ModelTimeoutError(timeout_seconds=30),
    ],
)
@patch.object(Bot, "send_message", new_callable=AsyncMock)
@patch.object(Message, "reply", new_callable=AsyncMock)
@patch("bot.callbacks.error.explain_error", new_callable=AsyncMock)
async def test_error_callback_skips_agent_for_model_provider_failure(
    mock_explain_error,
    mock_reply,
    mock_send_message,
    monkeypatch,
    error,
):
    monkeypatch.setattr(settings, "developer_chat_id", None)
    event = _make_event(error, _make_message())

    await error_callback(event, _make_bot())

    mock_explain_error.assert_not_awaited()
    mock_reply.assert_awaited_once()
    mock_send_message.assert_not_awaited()


@patch.object(Bot, "send_message", new_callable=AsyncMock)
@patch("bot.callbacks.error.async_create_page", new_callable=AsyncMock)
@patch("bot.callbacks.error.explain_error", new_callable=AsyncMock)
async def test_error_callback_preserves_original_traceback_when_diagnostics_page_fails(
    mock_explain_error,
    mock_create_page,
    mock_send_message,
    monkeypatch,
    caplog,
):
    monkeypatch.setattr(settings, "developer_chat_id", "456")
    mock_explain_error.return_value = ErrorExplanation(
        user_message="請稍後重試。",
        administrator_message="外部服務無回應。",
    )
    mock_create_page.side_effect = RuntimeError("Telegraph unavailable")
    secret = "credential=sensitive"
    event = _make_event(_make_error_with_traceback(secret), object())
    bot = _make_bot()

    with caplog.at_level(logging.ERROR, logger="bot.callbacks.error"):
        await error_callback(event, bot)

    notification = mock_send_message.await_args.kwargs["text"]
    assert "錯誤摘要：外部服務無回應。" in notification
    assert "診斷資料頁建立失敗" in notification
    assert "_make_error_with_traceback" in caplog.text
    assert secret not in caplog.text
