from typing import cast
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from agents import TResponseInputItem

from bot.callbacks.agent import AgentCallback
from bot.callbacks.agent import remove_tool_messages


@pytest.fixture
def mock_redis_session(monkeypatch):
    sessions: list[Mock] = []
    queued_items: list[list[dict[str, str]]] = []

    def set_next_items(*items: list[dict[str, str]]) -> None:
        queued_items.clear()
        queued_items.extend(items)

    def _factory(*args, **kwargs):
        session = Mock()
        default_items = queued_items.pop(0) if queued_items else []
        session.get_items = AsyncMock(return_value=default_items)
        session.set_items = AsyncMock()
        session._init_args = args
        session._init_kwargs = kwargs
        sessions.append(session)
        return session

    monkeypatch.setattr("bot.callbacks.agent.RedisSession", _factory)
    return {"sessions": sessions, "set_next_items": set_next_items}


# Helper functions


def test_remove_tool_messages_filters_tool_types():
    tool_messages = [
        cast(TResponseInputItem, {"type": "function_call", "content": "tool call"}),
        cast(TResponseInputItem, {"type": "function_call_output", "content": "tool output"}),
        cast(TResponseInputItem, {"type": "computer_call", "content": "computer call"}),
    ]

    result = remove_tool_messages(tool_messages)

    assert len(result) == 0


def test_remove_tool_messages_keeps_regular_types():
    regular_messages = [
        cast(TResponseInputItem, {"type": "text", "content": "Hello"}),
        cast(TResponseInputItem, {"type": "user", "content": "User message"}),
        cast(TResponseInputItem, {"type": "text", "content": "Another message"}),
    ]

    result = remove_tool_messages(regular_messages)

    assert len(result) == 3
    assert result == regular_messages


def test_remove_tool_messages_mixed_messages():
    tool_msg = cast(TResponseInputItem, {"type": "function_call", "content": "tool call"})
    text_msg = cast(TResponseInputItem, {"type": "text", "content": "Hello"})
    user_msg = cast(TResponseInputItem, {"type": "user", "content": "User message"})

    all_messages = [tool_msg, text_msg, user_msg]
    result = remove_tool_messages(all_messages)

    assert len(result) == 2
    assert tool_msg not in result
    assert text_msg in result
    assert user_msg in result


# AgentCallback setup


def test_agent_callback_init(mock_redis_session):
    mock_agent = Mock()

    callback = AgentCallback(mock_agent, max_cache_size=100)

    assert callback.agent == mock_agent
    assert callback.max_cache_size == 100


def test_agent_callback_init_default_cache_size(mock_redis_session):
    mock_agent = Mock()

    callback = AgentCallback(mock_agent)

    assert callback.max_cache_size == 50


def test_make_cache_key_message_based():
    mock_agent = Mock()
    callback = AgentCallback(mock_agent)

    key = callback._make_cache_key(message_id=67890, chat_id=12345)
    assert key == "bot:67890:12345"


# handle_message


@patch("bot.callbacks.agent.get_processed_message_text")
@patch("bot.callbacks.agent.Runner")
async def test_handle_message_simple(mock_runner, mock_get_processed_message_text, mock_redis_session):
    mock_agent = Mock()
    mock_get_processed_message_text.return_value = ("Hello, how are you?", None)

    mock_result = Mock()
    mock_result.new_items = ["item1", "item2"]
    mock_result.final_output = "I'm doing well, thank you!"
    mock_result.to_input_list.return_value = [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!"},
    ]
    mock_runner.run = AsyncMock(return_value=mock_result)

    mock_message = Mock()
    mock_message.reply_to_message = None
    mock_message.chat.id = 12345
    mock_new_message = Mock()
    mock_new_message.message_id = 67890
    mock_message.answer = AsyncMock(return_value=mock_new_message)

    callback = AgentCallback(mock_agent)
    await callback.handle_message(mock_message)

    mock_runner.run.assert_called_once()
    call_args = mock_runner.run.call_args
    assert call_args[1]["input"][0]["role"] == "user"

    mock_message.answer.assert_called_once_with("I'm doing well, thank you!", parse_mode="HTML")
    assert call_args[1]["input"][0]["content"] == "Hello, how are you?"

    sessions = mock_redis_session["sessions"]
    assert len(sessions) == 1
    sessions[0].set_items.assert_called_once()


@patch("bot.callbacks.agent.get_processed_message_text")
async def test_handle_message_empty_text(mock_get_processed_message_text, mock_redis_session):
    mock_agent = Mock()

    mock_get_processed_message_text.return_value = (None, None)
    mock_message = Mock()

    callback = AgentCallback(mock_agent)
    await callback.handle_message(mock_message)

    mock_get_processed_message_text.assert_called_once()


@patch("bot.callbacks.agent.get_processed_message_text")
@patch("bot.callbacks.agent.Runner")
async def test_cache_ttl_is_set(mock_runner, mock_get_processed_message_text, mock_redis_session):
    from bot.settings import settings

    mock_agent = Mock()

    mock_get_processed_message_text.return_value = ("Test message", None)

    mock_result = Mock()
    mock_result.new_items = []
    mock_result.final_output = "Response"
    mock_result.to_input_list.return_value = [
        {"role": "user", "content": "Test message"},
        {"role": "assistant", "content": "Response"},
    ]
    mock_runner.run = AsyncMock(return_value=mock_result)

    mock_message = Mock()
    mock_message.reply_to_message = None
    mock_message.chat.id = 12345
    mock_new_message = Mock()
    mock_new_message.message_id = 67890
    mock_message.answer = AsyncMock(return_value=mock_new_message)

    callback = AgentCallback(mock_agent)
    await callback.handle_message(mock_message)

    sessions = mock_redis_session["sessions"]
    assert len(sessions) == 1
    sessions[0].set_items.assert_called_once()
    assert sessions[0]._init_args[0] == "bot:67890:12345"
    assert sessions[0]._init_kwargs["ttl_seconds"] == settings.cache_ttl_seconds


@patch("bot.callbacks.agent.get_processed_message_text")
@patch("bot.callbacks.agent.Runner")
async def test_cache_persists_in_reply_thread(mock_runner, mock_get_processed_message_text, mock_redis_session):
    mock_agent = Mock()
    existing_messages = [
        {"role": "user", "content": "Previous message"},
        {"role": "assistant", "content": "Previous response"},
    ]
    mock_redis_session["set_next_items"](existing_messages)

    mock_get_processed_message_text.return_value = ("New message", None)

    mock_result = Mock()
    mock_result.new_items = []
    mock_result.final_output = "New response"
    mock_result.to_input_list.return_value = [
        {"role": "user", "content": "Previous message"},
        {"role": "assistant", "content": "Previous response"},
        {"role": "user", "content": "New message"},
        {"role": "assistant", "content": "New response"},
    ]
    mock_runner.run = AsyncMock(return_value=mock_result)

    mock_reply_to = Mock()
    mock_reply_to.message_id = 11111
    mock_message = Mock()
    mock_message.reply_to_message = mock_reply_to
    mock_message.chat.id = 12345
    mock_new_message = Mock()
    mock_new_message.message_id = 67890
    mock_message.answer = AsyncMock(return_value=mock_new_message)

    callback = AgentCallback(mock_agent)
    await callback.handle_message(mock_message)

    sessions = mock_redis_session["sessions"]
    assert len(sessions) == 2
    assert sessions[0]._init_args[0] == "bot:11111:12345"
    assert sessions[1]._init_args[0] == "bot:67890:12345"

    call_args = mock_runner.run.call_args
    input_messages = call_args[1]["input"]
    assert len(input_messages) == 3
    assert input_messages[0]["content"] == "Previous message"
    assert input_messages[1]["content"] == "Previous response"
    assert input_messages[2]["content"] == "New message"


# handle_command


@patch("bot.callbacks.agent.trace")
async def test_handle_command(mock_trace, mock_redis_session):
    mock_agent = Mock()

    mock_update = Mock()
    mock_update.message = Mock()

    callback = AgentCallback(mock_agent)
    callback.handle_message = AsyncMock()  # type: ignore[assignment]

    await callback.handle_command(mock_update, None)

    callback.handle_message.assert_called_once_with(mock_update.message)  # type: ignore
    mock_trace.assert_called_once_with("handle_command")


async def test_handle_command_no_message(mock_redis_session):
    mock_agent = Mock()

    mock_update = Mock()
    mock_update.message = None

    callback = AgentCallback(mock_agent)
    callback.handle_message = AsyncMock()  # type: ignore[assignment]

    await callback.handle_command(mock_update, None)

    callback.handle_message.assert_not_called()  # type: ignore


# handle_reply


@patch("bot.callbacks.agent.trace")
async def test_handle_reply_valid_reply_to_this_bot(mock_trace, mock_redis_session):
    mock_agent = Mock()

    mock_bot_user = Mock()
    mock_bot_user.is_bot = True
    mock_bot_user.id = 42

    mock_reply_message = Mock()
    mock_reply_message.from_user = mock_bot_user

    mock_message = Mock()
    mock_message.reply_to_message = mock_reply_message
    mock_message.bot.id = 42

    mock_update = Mock()
    mock_update.message = mock_message

    callback = AgentCallback(mock_agent)
    callback.handle_message = AsyncMock()  # type: ignore[assignment]

    await callback.handle_reply(mock_update, None)

    callback.handle_message.assert_called_once_with(mock_message)  # type: ignore
    mock_trace.assert_called_once_with("handle_reply")


async def test_handle_reply_to_other_bot_is_ignored(mock_redis_session):
    mock_agent = Mock()

    mock_other_bot_user = Mock()
    mock_other_bot_user.is_bot = True
    mock_other_bot_user.id = 999

    mock_reply_message = Mock()
    mock_reply_message.from_user = mock_other_bot_user

    mock_message = Mock()
    mock_message.reply_to_message = mock_reply_message
    mock_message.bot.id = 42

    mock_update = Mock()
    mock_update.message = mock_message

    callback = AgentCallback(mock_agent)
    callback.handle_message = AsyncMock()  # type: ignore[assignment]

    await callback.handle_reply(mock_update, None)

    callback.handle_message.assert_not_called()  # type: ignore


async def test_handle_reply_not_bot_reply(mock_redis_session):
    mock_agent = Mock()

    mock_human_user = Mock()
    mock_human_user.is_bot = False
    mock_human_user.id = 123

    mock_reply_message = Mock()
    mock_reply_message.from_user = mock_human_user

    mock_message = Mock()
    mock_message.reply_to_message = mock_reply_message
    mock_message.bot.id = 42

    mock_update = Mock()
    mock_update.message = mock_message

    callback = AgentCallback(mock_agent)
    callback.handle_message = AsyncMock()  # type: ignore[assignment]

    await callback.handle_reply(mock_update, None)

    callback.handle_message.assert_not_called()  # type: ignore


async def test_handle_reply_no_reply_message(mock_redis_session):
    mock_agent = Mock()

    mock_message = Mock()
    mock_message.reply_to_message = None

    mock_update = Mock()
    mock_update.message = mock_message

    callback = AgentCallback(mock_agent)
    callback.handle_message = AsyncMock()  # type: ignore[assignment]

    await callback.handle_reply(mock_update, None)

    callback.handle_message.assert_not_called()  # type: ignore
