import os
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from telegram.ext import filters

from bot.bot import get_bot_token
from bot.bot import get_chat_filter
from bot.bot import run_bot


class TestBotModule:
    def test_get_bot_token_success(self):
        """Test successful token retrieval"""
        with patch.dict(os.environ, {"BOT_TOKEN": "test_token_123"}):
            token = get_bot_token()
            assert token == "test_token_123"

    def test_get_bot_token_missing(self):
        """Test error when BOT_TOKEN is not set"""
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(ValueError, match="BOT_TOKEN is not set"),
        ):
            get_bot_token()

    def test_get_bot_token_empty(self):
        """Test error when BOT_TOKEN is empty"""
        with (
            patch.dict(os.environ, {"BOT_TOKEN": ""}),
            pytest.raises(ValueError, match="BOT_TOKEN is not set"),
        ):
            get_bot_token()

    def test_get_chat_filter_no_whitelist(self):
        """Test chat filter when no whitelist is specified"""
        with patch.dict(os.environ, {}, clear=True):
            chat_filter = get_chat_filter()
            assert chat_filter == filters.ALL

    def test_get_chat_filter_empty_whitelist(self):
        """Test chat filter when whitelist is empty"""
        with patch.dict(os.environ, {"BOT_WHITELIST": ""}):
            chat_filter = get_chat_filter()
            assert chat_filter == filters.ALL

    def test_get_chat_filter_single_chat(self):
        """Test chat filter with single chat ID"""
        with patch.dict(os.environ, {"BOT_WHITELIST": "123456789"}):
            chat_filter = get_chat_filter()
            # Should create a Chat filter, verify it's not ALL
            assert chat_filter != filters.ALL
            assert isinstance(chat_filter, filters.Chat)

    def test_get_chat_filter_multiple_chats(self):
        """Test chat filter with multiple chat IDs"""
        with patch.dict(os.environ, {"BOT_WHITELIST": "123456789,987654321"}):
            chat_filter = get_chat_filter()
            assert chat_filter != filters.ALL
            assert isinstance(chat_filter, filters.Chat)

    def test_get_chat_filter_with_spaces(self):
        """Test chat filter with spaces in whitelist"""
        with patch.dict(os.environ, {"BOT_WHITELIST": "123456789, 987654321, 555666777"}):
            chat_filter = get_chat_filter()
            assert chat_filter != filters.ALL
            assert isinstance(chat_filter, filters.Chat)

    def test_get_chat_filter_invalid_chat_id(self):
        """Test error handling for invalid chat IDs"""
        with (
            patch.dict(os.environ, {"BOT_WHITELIST": "invalid_id"}),
            pytest.raises(ValueError),
        ):
            get_chat_filter()

    @patch("bot.bot.AgentCallback")
    @patch("bot.bot.Application")
    @patch("bot.bot.get_bot_token")
    @patch("bot.bot.get_chat_filter")
    def test_run_bot_basic_setup(
        self, mock_get_chat_filter, mock_get_bot_token, mock_application_class, mock_agent_callback_class
    ):
        """Test basic bot setup and configuration"""
        # Setup mocks
        mock_get_bot_token.return_value = "test_token"
        mock_chat_filter = filters.ALL  # Use actual filter object
        mock_get_chat_filter.return_value = mock_chat_filter

        # Mock AgentCallback
        mock_agent_callback = Mock()
        mock_agent_callback.connect = AsyncMock()
        mock_agent_callback.cleanup = AsyncMock()
        mock_agent_callback.handle_command = AsyncMock()
        mock_agent_callback.handle_reply = AsyncMock()
        mock_agent_callback_class.from_config.return_value = mock_agent_callback

        # Mock Application
        mock_app_builder = Mock()
        mock_app = Mock()
        mock_app_builder.token.return_value = mock_app_builder
        mock_app_builder.post_init.return_value = mock_app_builder
        mock_app_builder.post_shutdown.return_value = mock_app_builder
        mock_app_builder.build.return_value = mock_app
        mock_application_class.builder.return_value = mock_app_builder

        # Mock run_polling to avoid infinite loop
        mock_app.run_polling = Mock()

        # Run the function
        run_bot("test_config.json")

        # Verify AgentCallback was created with correct config
        mock_agent_callback_class.from_config.assert_called_once_with("test_config.json")

        # Verify Application builder was configured correctly
        mock_app_builder.token.assert_called_once_with("test_token")
        mock_app_builder.post_init.assert_called_once()
        mock_app_builder.post_shutdown.assert_called_once()
        mock_app_builder.build.assert_called_once()

        # Verify handlers were added
        assert mock_app.add_handlers.called
        assert mock_app.add_handler.called
        assert mock_app.add_error_handler.called

        # Verify polling was started
        mock_app.run_polling.assert_called_once()

    @patch("bot.bot.AgentCallback")
    @patch("bot.bot.Application")
    @patch("bot.bot.get_bot_token")
    @patch("bot.bot.get_chat_filter")
    def test_run_bot_default_config(
        self, mock_get_chat_filter, mock_get_bot_token, mock_application_class, mock_agent_callback_class
    ):
        """Test bot run with default config file"""
        # Setup basic mocks
        mock_get_bot_token.return_value = "test_token"
        mock_get_chat_filter.return_value = filters.ALL

        mock_agent_callback = Mock()
        mock_agent_callback.connect = AsyncMock()
        mock_agent_callback.cleanup = AsyncMock()
        mock_agent_callback_class.from_config.return_value = mock_agent_callback

        mock_app_builder = Mock()
        mock_app = Mock()
        mock_app_builder.token.return_value = mock_app_builder
        mock_app_builder.post_init.return_value = mock_app_builder
        mock_app_builder.post_shutdown.return_value = mock_app_builder
        mock_app_builder.build.return_value = mock_app
        mock_application_class.builder.return_value = mock_app_builder
        mock_app.run_polling = Mock()

        # Run with default config
        run_bot()

        # Should use default config file
        mock_agent_callback_class.from_config.assert_called_once_with("config/default.json")

    @patch("bot.bot.AgentCallback")
    @patch("bot.bot.Application")
    @patch("bot.bot.get_bot_token")
    @patch("bot.bot.get_chat_filter")
    @patch.dict(os.environ, {"DEVELOPER_CHAT_ID": "123456789"})
    def test_run_bot_with_developer_chat(
        self, mock_get_chat_filter, mock_get_bot_token, mock_application_class, mock_agent_callback_class
    ):
        """Test bot setup with developer chat ID"""
        # Setup mocks
        mock_get_bot_token.return_value = "test_token"
        mock_get_chat_filter.return_value = filters.ALL

        mock_agent_callback = Mock()
        mock_agent_callback.connect = AsyncMock()
        mock_agent_callback.cleanup = AsyncMock()
        mock_agent_callback_class.from_config.return_value = mock_agent_callback

        mock_app_builder = Mock()
        mock_app = Mock()
        mock_app_builder.token.return_value = mock_app_builder
        mock_app_builder.post_init.return_value = mock_app_builder
        mock_app_builder.post_shutdown.return_value = mock_app_builder
        mock_app_builder.build.return_value = mock_app
        mock_application_class.builder.return_value = mock_app_builder
        mock_app.run_polling = Mock()

        # Run the function
        run_bot()

        # Verify error handler was added with developer chat ID
        mock_app.add_error_handler.assert_called_once()

        # Get the ErrorCallback instance that was passed
        error_callback_call = mock_app.add_error_handler.call_args
        assert error_callback_call is not None

    @patch("bot.bot.AgentCallback")
    @patch("bot.bot.Application")
    @patch("bot.bot.get_bot_token")
    @patch("bot.bot.get_chat_filter")
    def test_run_bot_handler_configuration(
        self, mock_get_chat_filter, mock_get_bot_token, mock_application_class, mock_agent_callback_class
    ):
        """Test that all expected handlers are configured"""
        # Setup mocks
        mock_get_bot_token.return_value = "test_token"
        mock_chat_filter = filters.ALL  # Use actual filter object
        mock_get_chat_filter.return_value = mock_chat_filter

        mock_agent_callback = Mock()
        mock_agent_callback.connect = AsyncMock()
        mock_agent_callback.cleanup = AsyncMock()
        mock_agent_callback.handle_command = Mock()
        mock_agent_callback.handle_reply = Mock()
        mock_agent_callback_class.from_config.return_value = mock_agent_callback

        mock_app_builder = Mock()
        mock_app = Mock()
        mock_app_builder.token.return_value = mock_app_builder
        mock_app_builder.post_init.return_value = mock_app_builder
        mock_app_builder.post_shutdown.return_value = mock_app_builder
        mock_app_builder.build.return_value = mock_app
        mock_application_class.builder.return_value = mock_app_builder
        mock_app.run_polling = Mock()

        # Run the function
        run_bot()

        # Verify add_handlers was called with command handlers
        assert mock_app.add_handlers.called
        handlers_call = mock_app.add_handlers.call_args[0][0]

        # Should have multiple command handlers
        assert len(handlers_call) > 0

        # Verify message handlers were added
        assert mock_app.add_handler.call_count == 2  # Reply handler and file handler

        # Verify error handler was added
        assert mock_app.add_error_handler.called
