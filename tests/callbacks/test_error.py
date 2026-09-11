from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

from aiogram import Bot
from aiogram.types import Message

from bot.agents.error import ErrorExplanation
from bot.callbacks.error import error_callback
from bot.settings import settings


def _make_event(error: Exception, update_event: object) -> Mock:
    event = Mock()
    event.exception = error
    event.update.event = update_event
    event.update.model_dump.return_value = {"update_id": 123}
    return event


def _make_message() -> Mock:
    message = Mock(spec=Message)
    message.reply = AsyncMock()
    return message


def _make_bot() -> Mock:
    bot = Mock(spec=Bot)
    bot.send_message = AsyncMock()
    return bot


@patch("bot.callbacks.error.async_create_page", new_callable=AsyncMock)
@patch("bot.callbacks.error.explain_error", new_callable=AsyncMock)
async def test_error_callback_explains_error_to_user_and_administrator(
    mock_explain_error,
    mock_create_page,
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
    message.reply.assert_awaited_once_with(
        explanation.user_message,
        parse_mode=None,
        allow_sending_without_reply=True,
    )
    mock_create_page.assert_awaited_once()
    bot.send_message.assert_awaited_once_with(
        chat_id="456",
        text=("錯誤摘要：ReadTimeout；請檢查上游服務連線。\n\n診斷資料：https://example.com/error"),
    )


@patch("bot.callbacks.error.async_create_page", new_callable=AsyncMock)
@patch("bot.callbacks.error.explain_error", new_callable=AsyncMock)
async def test_error_callback_notifies_user_without_configured_administrator(
    mock_explain_error,
    mock_create_page,
    monkeypatch,
):
    monkeypatch.setattr(settings, "developer_chat_id", None)
    explanation = ErrorExplanation(user_message="請先停止重試。", administrator_message="ValueError")
    mock_explain_error.return_value = explanation
    message = _make_message()
    event = _make_event(ValueError("bad input"), message)
    bot = _make_bot()

    await error_callback(event, bot)

    message.reply.assert_awaited_once()
    mock_create_page.assert_not_awaited()
    bot.send_message.assert_not_awaited()


@patch("bot.callbacks.error.async_create_page", new_callable=AsyncMock)
@patch("bot.callbacks.error.explain_error", new_callable=AsyncMock)
async def test_error_callback_notifies_administrator_without_originating_message(
    mock_explain_error,
    mock_create_page,
    monkeypatch,
):
    monkeypatch.setattr(settings, "developer_chat_id", "456")
    explanation = ErrorExplanation(user_message="請稍後重試。", administrator_message="背景工作失敗。")
    mock_explain_error.return_value = explanation
    mock_create_page.return_value = "https://example.com/error"
    event = _make_event(RuntimeError("background failure"), object())
    bot = _make_bot()

    await error_callback(event, bot)

    bot.send_message.assert_awaited_once()


@patch("bot.callbacks.error.explain_error", new_callable=AsyncMock)
async def test_error_callback_uses_error_derived_fallback_when_agent_fails(mock_explain_error, monkeypatch):
    monkeypatch.setattr(settings, "developer_chat_id", None)
    mock_explain_error.side_effect = RuntimeError("model unavailable")
    message = _make_message()
    event = _make_event(ValueError("invalid input"), message)

    await error_callback(event, _make_bot())

    response = message.reply.await_args.args[0]
    assert "處理資料時中止" in response
    assert "先不要重複傳送" in response
    assert "抱歉，處理您的請求時發生錯誤" not in response


@patch("bot.callbacks.error.async_create_page", new_callable=AsyncMock)
@patch("bot.callbacks.error.explain_error", new_callable=AsyncMock)
async def test_error_callback_still_notifies_administrator_when_diagnostics_page_fails(
    mock_explain_error,
    mock_create_page,
    monkeypatch,
):
    monkeypatch.setattr(settings, "developer_chat_id", "456")
    mock_explain_error.return_value = ErrorExplanation(
        user_message="請稍後重試。",
        administrator_message="外部服務無回應。",
    )
    mock_create_page.side_effect = RuntimeError("Telegraph unavailable")
    event = _make_event(RuntimeError("upstream unavailable"), object())
    bot = _make_bot()

    await error_callback(event, bot)

    notification = bot.send_message.await_args.kwargs["text"]
    assert "錯誤摘要：外部服務無回應。" in notification
    assert "診斷資料頁建立失敗" in notification
