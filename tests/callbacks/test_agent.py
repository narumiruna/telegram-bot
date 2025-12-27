import json
import os
import tempfile
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from mcp.client.stdio import StdioServerParameters

from bot.callbacks.agent import AgentCallback
from bot.callbacks.agent import load_mcp_config
from bot.callbacks.agent import remove_fake_id_messages
from bot.callbacks.agent import remove_tool_messages


class TestAgentHelperFunctions:
    def test_remove_tool_messages(self):
        """Test removal of tool-related messages"""
        messages = [
            {"type": "text", "content": "Hello"},
            {"type": "function_call", "content": "tool call"},
            {"type": "user", "content": "User message"},
            {"type": "function_call_output", "content": "tool output"},
            {"type": "computer_call", "content": "computer call"},
            {"type": "text", "content": "Another message"},
        ]

        result = remove_tool_messages(messages)

        # Should only keep non-tool messages
        expected = [
            {"type": "text", "content": "Hello"},
            {"type": "user", "content": "User message"},
            {"type": "text", "content": "Another message"},
        ]
        assert result == expected

    def test_remove_tool_messages_empty_list(self):
        """Test removal from empty list"""
        result = remove_tool_messages([])
        assert result == []

    def test_remove_tool_messages_no_tool_messages(self):
        """Test when no tool messages to remove"""
        messages = [
            {"type": "text", "content": "Hello"},
            {"type": "user", "content": "User message"},
        ]
        result = remove_tool_messages(messages)
        assert result == messages

    def test_remove_fake_id_messages(self):
        """Test removal of fake ID messages"""
        messages = [
            {"id": "real_id", "content": "Real message"},
            {"id": "__fake_id__", "content": "Fake message"},
            {"id": "another_real_id", "content": "Another real message"},
            {"id": "__fake_id__", "content": "Another fake message"},
        ]

        result = remove_fake_id_messages(messages)

        expected = [
            {"id": "real_id", "content": "Real message"},
            {"id": "another_real_id", "content": "Another real message"},
        ]
        assert result == expected

    def test_remove_fake_id_messages_no_fake_ids(self):
        """Test when no fake IDs to remove"""
        messages = [
            {"id": "real_id", "content": "Real message"},
            {"id": "another_real_id", "content": "Another real message"},
        ]
        result = remove_fake_id_messages(messages)
        assert result == messages


class TestLoadMcpConfig:
    def test_load_mcp_config_valid_file(self):
        """Test loading valid MCP configuration"""
        config_data = {
            "firecrawl": {
                "command": "npx",
                "args": ["-y", "@firecrawl/mcp-server-firecrawl"],
                "env": {"FIRECRAWL_API_KEY": "test_key"},
            },
            "yahoo_finance": {"command": "uvx", "args": ["yfmcp"], "env": {}},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            import json

            json.dump(config_data, f)
            temp_path = f.name

        try:
            result = load_mcp_config(temp_path)

            assert "firecrawl" in result
            assert "yahoo_finance" in result

            firecrawl_params = result["firecrawl"]
            assert firecrawl_params.command == "npx"
            assert firecrawl_params.args == ["-y", "@firecrawl/mcp-server-firecrawl"]
            assert firecrawl_params.env["FIRECRAWL_API_KEY"] == "test_key"

            yahoo_params = result["yahoo_finance"]
            assert yahoo_params.command == "uvx"
            assert yahoo_params.args == ["yfmcp"]
        finally:
            os.unlink(temp_path)

    @patch.dict(os.environ, {"TEST_API_KEY": "env_value"})
    def test_load_mcp_config_env_substitution(self):
        """Test environment variable substitution"""
        config_data = {
            "test_server": {
                "command": "test_cmd",
                "args": [],
                "env": {
                    "TEST_API_KEY": ""  # Empty value should be replaced
                },
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            import json

            json.dump(config_data, f)
            temp_path = f.name

        try:
            result = load_mcp_config(temp_path)
            assert result["test_server"].env["TEST_API_KEY"] == "env_value"
        finally:
            os.unlink(temp_path)

    def test_load_mcp_config_invalid_format(self):
        """Test error handling for invalid config format"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json")
            temp_path = f.name

        try:
            with pytest.raises((json.JSONDecodeError, ValueError)):
                load_mcp_config(temp_path)
        finally:
            os.unlink(temp_path)

    def test_load_mcp_config_invalid_structure(self):
        """Test error handling for invalid structure"""
        config_data = "not a dict"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            import json

            json.dump(config_data, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid configuration file"):
                load_mcp_config(temp_path)
        finally:
            os.unlink(temp_path)


class TestAgentCallback:
    @patch("bot.callbacks.agent.load_mcp_config")
    @patch("bot.callbacks.agent.get_openai_model")
    @patch("bot.callbacks.agent.get_openai_model_settings")
    @patch("bot.callbacks.agent.Agent")
    def test_from_config(self, mock_agent_class, mock_model_settings, mock_model, mock_load_config):
        """Test AgentCallback creation from config"""
        # Setup mocks
        mock_config = {"test_server": StdioServerParameters(command="test_cmd", args=["arg1"])}
        mock_load_config.return_value = mock_config
        mock_model.return_value = "test_model"
        mock_model_settings.return_value = {"temperature": 0.0}
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Call method
        result = AgentCallback.from_config("test_config.json")

        # Verify
        mock_load_config.assert_called_once_with("test_config.json")
        mock_agent_class.assert_called_once()
        assert isinstance(result, AgentCallback)
        assert result.agent == mock_agent

    @patch("bot.callbacks.agent.get_cache_from_env")
    def test_init(self, mock_get_cache):
        """Test AgentCallback initialization"""
        mock_agent = Mock()
        mock_cache = Mock()
        mock_get_cache.return_value = mock_cache

        callback = AgentCallback(mock_agent, max_cache_size=100)

        assert callback.agent == mock_agent
        assert callback.max_cache_size == 100
        assert callback.cache == mock_cache

    @patch("bot.callbacks.agent.get_cache_from_env")
    def test_init_default_cache_size(self, mock_get_cache):
        """Test AgentCallback initialization with default cache size"""
        mock_agent = Mock()
        mock_cache = Mock()
        mock_get_cache.return_value = mock_cache

        callback = AgentCallback(mock_agent)

        assert callback.max_cache_size == 50

    @patch("bot.callbacks.agent.get_cache_from_env")
    async def test_connect(self, mock_get_cache):
        """Test connecting MCP servers"""
        mock_agent = Mock()
        mock_cache = Mock()
        mock_get_cache.return_value = mock_cache

        # Create mock MCP servers
        mock_server1 = Mock()
        mock_server1.connect = AsyncMock()
        mock_server2 = Mock()
        mock_server2.connect = AsyncMock()

        mock_agent.mcp_servers = [mock_server1, mock_server2]

        callback = AgentCallback(mock_agent)
        await callback.connect()

        mock_server1.connect.assert_called_once()
        mock_server2.connect.assert_called_once()

    @patch("bot.callbacks.agent.get_cache_from_env")
    async def test_cleanup(self, mock_get_cache):
        """Test cleaning up MCP servers"""
        mock_agent = Mock()
        mock_cache = Mock()
        mock_get_cache.return_value = mock_cache

        # Create mock MCP servers
        mock_server1 = Mock()
        mock_server1.cleanup = AsyncMock()
        mock_server2 = Mock()
        mock_server2.cleanup = AsyncMock()

        mock_agent.mcp_servers = [mock_server1, mock_server2]

        callback = AgentCallback(mock_agent)
        await callback.cleanup()

        mock_server1.cleanup.assert_called_once()
        mock_server2.cleanup.assert_called_once()

    @patch("bot.callbacks.agent.get_cache_from_env")
    @patch("bot.callbacks.agent.async_load_url")
    @patch("bot.callbacks.agent.parse_url")
    async def test_load_url_content_with_url(self, mock_parse_url, mock_async_load_url, mock_get_cache):
        """Test loading URL content when URL is present"""
        mock_agent = Mock()
        mock_cache = Mock()
        mock_get_cache.return_value = mock_cache
        mock_parse_url.return_value = "https://example.com"
        mock_async_load_url.return_value = "URL content here"

        callback = AgentCallback(mock_agent)

        message_text = "Check this out: https://example.com"
        result = await callback.load_url_content(message_text)

        expected = (
            "Check this out: [URL content from https://example.com]:\n'''"
            "\nURL content here\n'''\n[END of URL content]\n"
        )
        assert result == expected
        mock_async_load_url.assert_called_once_with("https://example.com")

    @patch("bot.callbacks.agent.get_cache_from_env")
    @patch("bot.callbacks.agent.parse_url")
    async def test_load_url_content_no_url(self, mock_parse_url, mock_get_cache):
        """Test loading URL content when no URL is present"""
        mock_agent = Mock()
        mock_cache = Mock()
        mock_get_cache.return_value = mock_cache
        mock_parse_url.return_value = ""

        callback = AgentCallback(mock_agent)

        message_text = "Just a regular message"
        result = await callback.load_url_content(message_text)

        assert result == message_text

    @patch("bot.callbacks.agent.get_cache_from_env")
    @patch("bot.callbacks.agent.get_message_text")
    @patch("bot.callbacks.agent.Runner")
    async def test_handle_message_simple(self, mock_runner, mock_get_message_text, mock_get_cache):
        """Test handling a simple message without reply"""
        mock_agent = Mock()
        mock_cache = Mock()
        mock_cache.get = AsyncMock(return_value=[])
        mock_cache.set = AsyncMock()
        mock_get_cache.return_value = mock_cache

        mock_get_message_text.return_value = "Hello, how are you?"

        # Mock runner result
        mock_result = Mock()
        mock_result.new_items = ["item1", "item2"]
        mock_result.final_output = "I'm doing well, thank you!"
        mock_result.to_input_list.return_value = [
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you!"},
        ]
        mock_runner.run = AsyncMock(return_value=mock_result)

        # Mock message
        mock_message = Mock()
        mock_message.reply_to_message = None
        mock_message.chat.id = 12345
        mock_new_message = Mock()
        mock_new_message.id = 67890
        mock_message.reply_text = AsyncMock(return_value=mock_new_message)

        callback = AgentCallback(mock_agent)
        await callback.handle_message(mock_message)

        # Verify runner was called with correct input
        mock_runner.run.assert_called_once()
        call_args = mock_runner.run.call_args
        assert call_args[1]["input"][0]["role"] == "user"
        assert call_args[1]["input"][0]["content"] == "Hello, how are you?"

        # Verify reply was sent
        mock_message.reply_text.assert_called_once_with("I'm doing well, thank you!")

        # Verify cache was updated
        mock_cache.set.assert_called_once()

    @patch("bot.callbacks.agent.get_cache_from_env")
    @patch("bot.callbacks.agent.get_message_text")
    async def test_handle_message_empty_text(self, mock_get_message_text, mock_get_cache):
        """Test handling message with empty text"""
        mock_agent = Mock()
        mock_cache = Mock()
        mock_get_cache.return_value = mock_cache

        mock_get_message_text.return_value = ""
        mock_message = Mock()

        callback = AgentCallback(mock_agent)
        await callback.handle_message(mock_message)

        # Should return early without processing
        mock_get_message_text.assert_called_once()

    @patch("bot.callbacks.agent.get_cache_from_env")
    @patch("bot.callbacks.agent.trace")
    async def test_handle_command(self, mock_trace, mock_get_cache):
        """Test handling command update"""
        mock_agent = Mock()
        mock_cache = Mock()
        mock_get_cache.return_value = mock_cache

        mock_update = Mock()
        mock_update.message = Mock()

        callback = AgentCallback(mock_agent)
        # Mock handle_message to avoid complex setup
        callback.handle_message = AsyncMock()

        await callback.handle_command(mock_update, None)

        callback.handle_message.assert_called_once_with(mock_update.message)
        mock_trace.assert_called_once_with("handle_command")

    @patch("bot.callbacks.agent.get_cache_from_env")
    async def test_handle_command_no_message(self, mock_get_cache):
        """Test handling command with no message"""
        mock_agent = Mock()
        mock_cache = Mock()
        mock_get_cache.return_value = mock_cache

        mock_update = Mock()
        mock_update.message = None

        callback = AgentCallback(mock_agent)
        callback.handle_message = AsyncMock()

        await callback.handle_command(mock_update, None)

        # Should return early without calling handle_message
        callback.handle_message.assert_not_called()

    @patch("bot.callbacks.agent.get_cache_from_env")
    @patch("bot.callbacks.agent.trace")
    async def test_handle_reply_valid_bot_reply(self, mock_trace, mock_get_cache):
        """Test handling reply to bot message"""
        mock_agent = Mock()
        mock_cache = Mock()
        mock_get_cache.return_value = mock_cache

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
        callback.handle_message = AsyncMock()

        await callback.handle_reply(mock_update, None)

        callback.handle_message.assert_called_once_with(mock_message)
        mock_trace.assert_called_once_with("handle_reply")

    @patch("bot.callbacks.agent.get_cache_from_env")
    async def test_handle_reply_not_bot_reply(self, mock_get_cache):
        """Test handling reply to non-bot message"""
        mock_agent = Mock()
        mock_cache = Mock()
        mock_get_cache.return_value = mock_cache

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
        callback.handle_message = AsyncMock()

        await callback.handle_reply(mock_update, None)

        # Should not call handle_message for replies to humans
        callback.handle_message.assert_not_called()

    @patch("bot.callbacks.agent.get_cache_from_env")
    async def test_handle_reply_no_reply_message(self, mock_get_cache):
        """Test handling message that's not a reply"""
        mock_agent = Mock()
        mock_cache = Mock()
        mock_get_cache.return_value = mock_cache

        mock_message = Mock()
        mock_message.reply_to_message = None

        mock_update = Mock()
        mock_update.message = mock_message

        callback = AgentCallback(mock_agent)
        callback.handle_message = AsyncMock()

        await callback.handle_reply(mock_update, None)

        # Should not call handle_message for non-reply messages
        callback.handle_message.assert_not_called()

    def test_make_cache_key_message_based(self):
        """Test that cache key is based on message_id and chat_id"""
        mock_agent = Mock()
        callback = AgentCallback(mock_agent)

        key = callback._make_cache_key(message_id=67890, chat_id=12345)
        assert key == "bot:67890:12345"

    @patch("bot.callbacks.agent.get_cache_from_env")
    @patch("bot.callbacks.agent.get_message_text")
    @patch("bot.callbacks.agent.Runner")
    async def test_cache_ttl_is_set(self, mock_runner, mock_get_message_text, mock_get_cache):
        """Test that cache is saved with TTL"""
        from bot.constants import CACHE_TTL_SECONDS

        mock_agent = Mock()
        mock_cache = Mock()
        mock_cache.get = AsyncMock(return_value=[])
        mock_cache.set = AsyncMock()
        mock_get_cache.return_value = mock_cache

        mock_get_message_text.return_value = "Test message"

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
        mock_new_message.id = 67890
        mock_message.reply_text = AsyncMock(return_value=mock_new_message)

        callback = AgentCallback(mock_agent)
        await callback.handle_message(mock_message)

        # Verify cache.set was called with TTL
        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        assert call_args[0][0] == "bot:67890:12345"  # cache key (new_message.id:chat.id)
        assert call_args[1]["ttl"] == CACHE_TTL_SECONDS  # TTL parameter

    @patch("bot.callbacks.agent.get_cache_from_env")
    @patch("bot.callbacks.agent.get_message_text")
    @patch("bot.callbacks.agent.Runner")
    async def test_cache_persists_in_reply_thread(self, mock_runner, mock_get_message_text, mock_get_cache):
        """Test that cache persists conversation history when replying to a message"""
        mock_agent = Mock()
        mock_cache = Mock()

        # Simulate existing conversation in cache
        existing_messages = [
            {"role": "user", "content": "Previous message"},
            {"role": "assistant", "content": "Previous response"},
        ]
        mock_cache.get = AsyncMock(return_value=existing_messages)
        mock_cache.set = AsyncMock()
        mock_get_cache.return_value = mock_cache

        mock_get_message_text.return_value = "New message"

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
        mock_reply_to.id = 11111
        mock_message = Mock()
        mock_message.reply_to_message = mock_reply_to
        mock_message.chat.id = 12345
        mock_new_message = Mock()
        mock_new_message.id = 67890
        mock_message.reply_text = AsyncMock(return_value=mock_new_message)

        callback = AgentCallback(mock_agent)
        await callback.handle_message(mock_message)

        # Verify cache.get was called with reply_to_message's key
        mock_cache.get.assert_called_once_with("bot:11111:12345", default=[])

        # Verify runner received existing messages plus new message
        call_args = mock_runner.run.call_args
        input_messages = call_args[1]["input"]
        assert len(input_messages) == 3  # 2 existing + 1 new
        assert input_messages[0]["content"] == "Previous message"
        assert input_messages[1]["content"] == "Previous response"
        assert input_messages[2]["content"] == "New message"
