from typing import cast
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

from agents import TResponseInputItem
from aiogram.types import User

from bot.callbacks.agent import AgentCallback

# AgentCallback setup


def test_agent_callback_init():
    mock_agent = Mock()

    callback = AgentCallback(mock_agent, max_cache_size=100)

    assert callback.agent == mock_agent
    assert callback.max_cache_size == 100
    assert callback.memory == {}


def test_agent_callback_init_default_cache_size():
    mock_agent = Mock()

    callback = AgentCallback(mock_agent)

    assert callback.max_cache_size == 50


# handle_message


@patch("bot.callbacks.agent.get_processed_message_text")
@patch("bot.callbacks.agent.Runner")
async def test_handle_message_simple(mock_runner, mock_get_processed_message_text):
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
    mock_message.reply = AsyncMock(return_value=mock_new_message)

    callback = AgentCallback(mock_agent)
    await callback.handle_message(mock_message)

    mock_runner.run.assert_called_once()
    call_args = mock_runner.run.call_args
    assert call_args[1]["input"][0]["role"] == "user"

    mock_message.reply.assert_called_once_with(
        "I'm doing well, thank you!",
        parse_mode="HTML",
        allow_sending_without_reply=True,
    )
    assert call_args[1]["input"][0]["content"] == "Hello, how are you?"

    assert callback.memory["12345"] == mock_result.to_input_list.return_value


@patch("bot.callbacks.agent.get_processed_message_text")
async def test_handle_message_empty_text(mock_get_processed_message_text):
    mock_agent = Mock()

    mock_get_processed_message_text.return_value = (None, None)
    mock_message = Mock()

    callback = AgentCallback(mock_agent)
    await callback.handle_message(mock_message)

    mock_get_processed_message_text.assert_called_once()


@patch("bot.callbacks.agent.get_processed_message_text")
@patch("bot.callbacks.agent.Runner")
async def test_memory_isolated_between_chats(mock_runner, mock_get_processed_message_text):
    mock_agent = Mock()
    mock_get_processed_message_text.return_value = ("Test message", None)

    first_result = Mock()
    first_result.new_items = []
    first_result.final_output = "Response one"
    first_result.to_input_list.return_value = [
        {"role": "user", "content": "Test message"},
        {"role": "assistant", "content": "Response one"},
    ]
    second_result = Mock()
    second_result.new_items = []
    second_result.final_output = "Response two"
    second_result.to_input_list.return_value = [
        {"role": "user", "content": "Test message"},
        {"role": "assistant", "content": "Response two"},
    ]
    mock_runner.run = AsyncMock(side_effect=[first_result, second_result])

    first_message = Mock()
    first_message.reply_to_message = None
    first_message.chat.id = 12345
    first_new_message = Mock()
    first_new_message.message_id = 11111
    first_message.reply = AsyncMock(return_value=first_new_message)

    second_message = Mock()
    second_message.reply_to_message = None
    second_message.chat.id = 67890
    second_new_message = Mock()
    second_new_message.message_id = 22222
    second_message.reply = AsyncMock(return_value=second_new_message)

    callback = AgentCallback(mock_agent)
    await callback.handle_message(first_message)
    await callback.handle_message(second_message)

    assert callback.memory["12345"] == first_result.to_input_list.return_value
    assert callback.memory["67890"] == second_result.to_input_list.return_value


@patch("bot.callbacks.agent.get_processed_message_text")
@patch("bot.callbacks.agent.Runner")
async def test_memory_persists_by_chat_id(mock_runner, mock_get_processed_message_text):
    mock_agent = Mock()
    existing_messages = [
        {"role": "user", "content": "Previous message"},
        {"role": "assistant", "content": "Previous response"},
    ]

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

    mock_message = Mock()
    mock_message.reply_to_message = None
    mock_message.chat.id = 12345
    mock_new_message = Mock()
    mock_new_message.message_id = 67890
    mock_message.reply = AsyncMock(return_value=mock_new_message)

    callback = AgentCallback(mock_agent)
    callback.memory["12345"] = cast(list[TResponseInputItem], existing_messages.copy())
    await callback.handle_message(mock_message)

    call_args = mock_runner.run.call_args
    input_messages = call_args[1]["input"]
    assert len(input_messages) == 3
    assert input_messages[0]["content"] == "Previous message"
    assert input_messages[1]["content"] == "Previous response"
    assert input_messages[2]["content"] == "New message"


@patch("bot.callbacks.agent.get_processed_message_text")
@patch("bot.callbacks.agent.Runner")
async def test_memory_trimmed_to_max_cache_size(mock_runner, mock_get_processed_message_text):
    mock_agent = Mock()
    mock_get_processed_message_text.return_value = ("New message", None)

    mock_result = Mock()
    mock_result.new_items = []
    mock_result.final_output = "New response"
    mock_result.to_input_list.return_value = [
        {"role": "user", "content": "m1"},
        {"role": "assistant", "content": "m2"},
        {"role": "user", "content": "m3"},
    ]
    mock_runner.run = AsyncMock(return_value=mock_result)

    mock_message = Mock()
    mock_message.reply_to_message = None
    mock_message.chat.id = 12345
    mock_new_message = Mock()
    mock_new_message.message_id = 67890
    mock_message.reply = AsyncMock(return_value=mock_new_message)

    callback = AgentCallback(mock_agent, max_cache_size=2)
    await callback.handle_message(mock_message)

    assert callback.memory["12345"] == [
        {"role": "assistant", "content": "m2"},
        {"role": "user", "content": "m3"},
    ]


def _build_message(
    text: str,
    *,
    chat_id: int = 12345,
    user: User | None = None,
    reply_to_message=None,
):
    message = Mock()
    message.text = text
    message.caption = None
    message.from_user = user or User(id=123, is_bot=False, first_name="TestUser", username="testuser")
    message.reply_to_message = reply_to_message
    message.chat.id = chat_id
    message.reply = AsyncMock()
    return message


def _build_runner_result() -> Mock:
    result = Mock()
    result.new_items = []
    result.final_output = "ok"
    result.to_input_list.return_value = [
        {"role": "user", "content": "stored"},
        {"role": "assistant", "content": "ok"},
    ]
    return result


@patch("bot.callbacks.utils.load_url")
@patch("bot.callbacks.agent.Runner")
async def test_handle_message_reply_keeps_reply_and_current_text(mock_runner, mock_load_url):
    mock_runner.run = AsyncMock(return_value=_build_runner_result())
    mock_load_url.return_value = "unused"

    reply_message = _build_message("Previous bot answer")
    message = _build_message("Please expand this", reply_to_message=reply_message)

    callback = AgentCallback(Mock())
    await callback.handle_message(message)

    input_messages = mock_runner.run.call_args.kwargs["input"]
    assert input_messages[-1]["content"] == (
        "Replied message:\nTestUser(testuser): Previous bot answer\n\n"
        "Current message:\nTestUser(testuser): Please expand this"
    )


@patch("bot.callbacks.utils.load_url")
@patch("bot.callbacks.agent.Runner")
async def test_handle_message_reply_with_current_url_keeps_current_text_in_runner_input(mock_runner, mock_load_url):
    mock_runner.run = AsyncMock(return_value=_build_runner_result())
    mock_load_url.return_value = "Loaded URL content"

    reply_message = _build_message("Previous bot answer")
    message = _build_message("Please summarize https://example.com", reply_to_message=reply_message)

    callback = AgentCallback(Mock())
    await callback.handle_message(message)

    input_messages = mock_runner.run.call_args.kwargs["input"]
    assert input_messages[-1]["content"] == (
        "Replied message:\nTestUser(testuser): Previous bot answer\n\n"
        "Current message:\nTestUser(testuser): Please summarize https://example.com\n\n"
        "URL content from https://example.com:\nLoaded URL content"
    )


@patch("bot.callbacks.utils.load_url")
@patch("bot.callbacks.agent.Runner")
async def test_handle_message_reply_with_reply_url_does_not_drop_current_text(mock_runner, mock_load_url):
    mock_runner.run = AsyncMock(return_value=_build_runner_result())
    mock_load_url.return_value = "Loaded URL content"

    reply_message = _build_message("See https://example.com")
    message = _build_message("What changed?", reply_to_message=reply_message)

    callback = AgentCallback(Mock())
    await callback.handle_message(message)

    input_messages = mock_runner.run.call_args.kwargs["input"]
    assert input_messages[-1]["content"] == (
        "Replied message:\nTestUser(testuser): See https://example.com\n\n"
        "Current message:\nTestUser(testuser): What changed?\n\n"
        "URL content from https://example.com:\nLoaded URL content"
    )


# handle_command


@patch("bot.callbacks.agent.trace")
async def test_handle_command(mock_trace):
    mock_agent = Mock()

    mock_update = Mock()
    mock_update.message = Mock()

    callback = AgentCallback(mock_agent)
    with patch.object(callback, "handle_message", new_callable=AsyncMock) as mock_handle_message:
        await callback.handle_command(mock_update, None)
    mock_handle_message.assert_called_once_with(mock_update.message)
    mock_trace.assert_called_once_with("handle_command")


async def test_handle_command_no_message():
    mock_agent = Mock()

    mock_update = Mock()
    mock_update.message = None

    callback = AgentCallback(mock_agent)
    with patch.object(callback, "handle_message", new_callable=AsyncMock) as mock_handle_message:
        await callback.handle_command(mock_update, None)
    mock_handle_message.assert_not_called()


# handle_reply


@patch("bot.callbacks.agent.trace")
async def test_handle_reply_valid_reply_to_this_bot(mock_trace):
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
    with patch.object(callback, "handle_message", new_callable=AsyncMock) as mock_handle_message:
        await callback.handle_reply(mock_update, None)
    mock_handle_message.assert_called_once_with(mock_message)
    mock_trace.assert_called_once_with("handle_reply")


async def test_handle_reply_to_other_bot_is_ignored():
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
    with patch.object(callback, "handle_message", new_callable=AsyncMock) as mock_handle_message:
        await callback.handle_reply(mock_update, None)
    mock_handle_message.assert_not_called()


async def test_handle_reply_not_bot_reply():
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
    with patch.object(callback, "handle_message", new_callable=AsyncMock) as mock_handle_message:
        await callback.handle_reply(mock_update, None)
    mock_handle_message.assert_not_called()


async def test_handle_reply_no_reply_message():
    mock_agent = Mock()

    mock_message = Mock()
    mock_message.reply_to_message = None

    mock_update = Mock()
    mock_update.message = mock_message

    callback = AgentCallback(mock_agent)
    with patch.object(callback, "handle_message", new_callable=AsyncMock) as mock_handle_message:
        await callback.handle_reply(mock_update, None)
    mock_handle_message.assert_not_called()
