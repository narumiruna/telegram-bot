from typing import cast
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from agents import TResponseInputItem
from aiogram.types import Message

from bot.callbacks.agent import Agent
from bot.callbacks.agent import AgentCallback
from bot.callbacks.agent import remove_tool_messages


class TestAgentHelperFunctions:
    def test_remove_tool_messages_filters_tool_types(self):
        """Test that tool message types are filtered out"""
        tool_messages = [
            cast(TResponseInputItem, {"type": "function_call", "content": "tool call"}),
            cast(TResponseInputItem, {"type": "function_call_output", "content": "tool output"}),
            cast(TResponseInputItem, {"type": "computer_call", "content": "computer call"}),
        ]

        result = remove_tool_messages(tool_messages)

        # All tool messages should be filtered out
        assert len(result) == 0

    def test_remove_tool_messages_keeps_regular_types(self):
        """Test that regular message types are kept"""
        regular_messages = [
            cast(TResponseInputItem, {"type": "text", "content": "Hello"}),
            cast(TResponseInputItem, {"type": "user", "content": "User message"}),
            cast(TResponseInputItem, {"type": "text", "content": "Another message"}),
        ]

        result = remove_tool_messages(regular_messages)

        # All regular messages should be kept
        assert len(result) == 3
        assert result == regular_messages

    def test_remove_tool_messages_mixed_messages(self):  # noqa: C901
        """Test filtering with mixed message types"""
        # Create test data outside function to reduce complexity
        tool_msg = cast(TResponseInputItem, {"type": "function_call", "content": "tool call"})
        text_msg = cast(TResponseInputItem, {"type": "text", "content": "Hello"})
        user_msg = cast(TResponseInputItem, {"type": "user", "content": "User message"})

        all_messages = [tool_msg, text_msg, user_msg]
        result = remove_tool_messages(all_messages)

        # Should only have regular messages
        assert len(result) == 2
        assert tool_msg not in result
        assert text_msg in result
        assert user_msg in result

        class DummyAgent(Agent):
            def __init__(self, name="dummy"):
                super().__init__(name=name)

            async def __call__(self, *args, **kwargs):
                return None

        @pytest.mark.asyncio
        async def test_agent_callback_handle_message(monkeypatch):
            class DummyResult:
                def __init__(self):
                    self.new_items = ["item1", "item2"]
                    self.final_output = "final output"

                def to_input_list(self):
                    return [1, 2, 3]

            monkeypatch.setattr("bot.callbacks.agent.Runner.run", AsyncMock(return_value=DummyResult()))

            callback = AgentCallback(DummyAgent(name="dummy"), max_cache_size=2)
            message = Mock(spec=Message)
            message.text = "hello"
            message.answer = AsyncMock()
            await callback.handle_message(message)
            message.answer.assert_called()

        @pytest.mark.asyncio
        async def test_agent_callback_handle_message_trims_history(monkeypatch):
            class DummyResult:
                def __init__(self):
                    self.new_items = ["item1"]
                    self.final_output = "output"

                def to_input_list(self):
                    return list(range(10))

            monkeypatch.setattr("bot.callbacks.agent.Runner.run", AsyncMock(return_value=DummyResult()))

            callback = AgentCallback(DummyAgent(name="dummy"), max_cache_size=5)
            message = Mock(spec=Message)
            message.text = "hi"
            message.answer = AsyncMock()
            await callback.handle_message(message)
            message.answer.assert_called()

        @pytest.mark.asyncio
        async def test_agent_callback_handle_message_with_none(monkeypatch):
            class DummyResult:
                def __init__(self):
                    self.new_items = []
                    self.final_output = ""

                def to_input_list(self):
                    return []

            monkeypatch.setattr("bot.callbacks.agent.Runner.run", AsyncMock(return_value=DummyResult()))

            callback = AgentCallback(DummyAgent(name="dummy"), max_cache_size=1)
            message = Mock(spec=Message)
            message.text = None
            message.answer = AsyncMock()
            await callback.handle_message(message)
            message.answer.assert_called()

        # (Removed invalid/unfinished code block here)


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


class TestAgentCallback:
    def test_init(self, mock_redis_session):
        """Test AgentCallback initialization"""
        mock_agent = Mock()

        callback = AgentCallback(mock_agent, max_cache_size=100)

        assert callback.agent == mock_agent
        assert callback.max_cache_size == 100

    def test_init_default_cache_size(self, mock_redis_session):
        """Test AgentCallback initialization with default cache size"""
        mock_agent = Mock()

        callback = AgentCallback(mock_agent)

        assert callback.max_cache_size == 50

    @patch("bot.callbacks.agent.get_processed_message_text")
    @patch("bot.callbacks.agent.Runner")
    async def test_handle_message_simple(self, mock_runner, mock_get_processed_message_text, mock_redis_session):
        """Test handling a simple message without reply"""
        mock_agent = Mock()
        mock_get_processed_message_text.return_value = ("Hello, how are you?", None)

        # Mock runner result
        mock_result = Mock()
        mock_result.new_items = ["item1", "item2"]
        mock_result.final_output = "I'm doing well, thank you!"
        mock_result.to_input_list.return_value = [
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you!"},
        ]
        mock_runner.run = AsyncMock(return_value=mock_result)

        # Mock message and MessageResponse
        mock_message = Mock()
        mock_message.reply_to_message = None
        mock_message.chat.id = 12345
        mock_new_message = Mock()
        mock_new_message.message_id = 67890
        mock_message.answer = AsyncMock(return_value=mock_new_message)

        callback = AgentCallback(mock_agent)
        await callback.handle_message(mock_message)

        # Verify runner was called with correct input
        mock_runner.run.assert_called_once()
        call_args = mock_runner.run.call_args
        assert call_args[1]["input"][0]["role"] == "user"

        # Verify reply_text was called with MessageResponse content
        mock_message.answer.assert_called_once_with("I'm doing well, thank you!", parse_mode="HTML")
        assert call_args[1]["input"][0]["content"] == "Hello, how are you?"

        # Verify cache was updated
        sessions = mock_redis_session["sessions"]
        assert len(sessions) == 1
        sessions[0].set_items.assert_called_once()

    @patch("bot.callbacks.agent.get_processed_message_text")
    async def test_handle_message_empty_text(self, mock_get_processed_message_text, mock_redis_session):
        """Test handling message with empty text"""
        mock_agent = Mock()

        mock_get_processed_message_text.return_value = (None, None)
        mock_message = Mock()

        callback = AgentCallback(mock_agent)
        await callback.handle_message(mock_message)

        # Should return early without processing
        mock_get_processed_message_text.assert_called_once()

    @patch("bot.callbacks.agent.trace")
    async def test_handle_command(self, mock_trace, mock_redis_session):
        """Test handling command update"""
        mock_agent = Mock()

        mock_update = Mock()
        mock_update.message = Mock()

        callback = AgentCallback(mock_agent)
        # Mock handle_message to avoid complex setup
        callback.handle_message = AsyncMock()  # type: ignore[assignment]

        await callback.handle_command(mock_update, None)

        callback.handle_message.assert_called_once_with(mock_update.message)  # type: ignore
        mock_trace.assert_called_once_with("handle_command")

    async def test_handle_command_no_message(self, mock_redis_session):
        """Test handling command with no message"""
        mock_agent = Mock()

        mock_update = Mock()
        mock_update.message = None

        callback = AgentCallback(mock_agent)
        callback.handle_message = AsyncMock()  # type: ignore[assignment]

        await callback.handle_command(mock_update, None)

        # Should return early without calling handle_message
        callback.handle_message.assert_not_called()  # type: ignore

    @patch("bot.callbacks.agent.trace")
    async def test_handle_reply_valid_bot_reply(self, mock_trace, mock_redis_session):
        """Test handling reply to bot message"""
        mock_agent = Mock()

        # Setup valid reply to bot message
        mock_bot_user = Mock()
        mock_bot_user.is_bot = True

        mock_reply_message = Mock()
        mock_reply_message.from_user = mock_bot_user

        mock_message = Mock()
        mock_message.reply_to_message = mock_reply_message

        mock_update = Mock()
        mock_update.message = mock_message

        callback = AgentCallback(mock_agent)
        callback.handle_message = AsyncMock()  # type: ignore[assignment]

        await callback.handle_reply(mock_update, None)

        callback.handle_message.assert_called_once_with(mock_message)  # type: ignore
        mock_trace.assert_called_once_with("handle_reply")

    async def test_handle_reply_not_bot_reply(self, mock_redis_session):
        """Test handling reply to non-bot message"""
        mock_agent = Mock()

        # Setup reply to human message
        mock_human_user = Mock()
        mock_human_user.is_bot = False

        mock_reply_message = Mock()
        mock_reply_message.from_user = mock_human_user

        mock_message = Mock()
        mock_message.reply_to_message = mock_reply_message

        mock_update = Mock()
        mock_update.message = mock_message

        callback = AgentCallback(mock_agent)
        callback.handle_message = AsyncMock()  # type: ignore[assignment]

        await callback.handle_reply(mock_update, None)

        # Should not call handle_message for replies to humans
        callback.handle_message.assert_not_called()  # type: ignore

    async def test_handle_reply_no_reply_message(self, mock_redis_session):
        """Test handling message that's not a reply"""
        mock_agent = Mock()

        mock_message = Mock()
        mock_message.reply_to_message = None

        mock_update = Mock()
        mock_update.message = mock_message

        callback = AgentCallback(mock_agent)
        callback.handle_message = AsyncMock()  # type: ignore[assignment]

        await callback.handle_reply(mock_update, None)

        # Should not call handle_message for non-reply messages
        callback.handle_message.assert_not_called()  # type: ignore

    def test_make_cache_key_message_based(self):
        """Test that cache key is based on message_id and chat_id"""
        mock_agent = Mock()
        callback = AgentCallback(mock_agent)

        key = callback._make_cache_key(message_id=67890, chat_id=12345)
        assert key == "bot:67890:12345"

    @patch("bot.callbacks.agent.get_processed_message_text")
    @patch("bot.callbacks.agent.Runner")
    async def test_cache_ttl_is_set(self, mock_runner, mock_get_processed_message_text, mock_redis_session):
        """Test that cache is saved with TTL"""
        from bot.settings import settings

        mock_agent = Mock()

        mock_get_processed_message_text.return_value = ("Test message", None)

        # Mock runner result
        mock_result = Mock()
        mock_result.new_items = []
        mock_result.final_output = "Response"
        mock_result.to_input_list.return_value = [
            {"role": "user", "content": "Test message"},
            {"role": "assistant", "content": "Response"},
        ]
        mock_runner.run = AsyncMock(return_value=mock_result)

        # Mock message
        mock_message = Mock()
        mock_message.reply_to_message = None
        mock_message.chat.id = 12345
        mock_new_message = Mock()
        mock_new_message.message_id = 67890
        mock_message.answer = AsyncMock(return_value=mock_new_message)

        callback = AgentCallback(mock_agent)
        await callback.handle_message(mock_message)

        # Verify session was created with TTL
        sessions = mock_redis_session["sessions"]
        assert len(sessions) == 1
        sessions[0].set_items.assert_called_once()
        assert sessions[0]._init_args[0] == "bot:67890:12345"
        assert sessions[0]._init_kwargs["ttl_seconds"] == settings.cache_ttl_seconds

    @patch("bot.callbacks.agent.get_processed_message_text")
    @patch("bot.callbacks.agent.Runner")
    async def test_cache_persists_in_reply_thread(
        self, mock_runner, mock_get_processed_message_text, mock_redis_session
    ):
        """Test that cache persists conversation history when replying to a message"""
        mock_agent = Mock()
        # Simulate existing conversation in cache
        existing_messages = [
            {"role": "user", "content": "Previous message"},
            {"role": "assistant", "content": "Previous response"},
        ]
        mock_redis_session["set_next_items"](existing_messages)

        mock_get_processed_message_text.return_value = ("New message", None)

        # Mock runner result
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

        # Mock message with reply_to_message
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

        # Verify runner received existing messages plus new message
        call_args = mock_runner.run.call_args
        input_messages = call_args[1]["input"]
        assert len(input_messages) == 3  # 2 existing + 1 new
        assert input_messages[0]["content"] == "Previous message"
        assert input_messages[1]["content"] == "Previous response"
        assert input_messages[2]["content"] == "New message"
