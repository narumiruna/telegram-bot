from unittest.mock import Mock
from unittest.mock import patch

import pytest

from bot.cli import main


class TestCLI:
    @patch("bot.cli.typer.run")
    @patch("bot.cli.configure_logfire")
    @patch("bot.cli.load_dotenv")
    @patch("bot.cli.find_dotenv")
    def test_main_success(self, mock_find_dotenv, mock_load_dotenv, mock_configure_logfire, mock_typer_run):
        """Test successful execution of main function"""
        # Setup mocks
        mock_find_dotenv.return_value = ".env"
        mock_load_dotenv.return_value = True

        # Call main
        main()

        # Verify all components were called
        mock_find_dotenv.assert_called_once_with(
            raise_error_if_not_found=True,
            usecwd=True,
        )
        mock_load_dotenv.assert_called_once_with(
            ".env",
            override=True,
        )
        mock_configure_logfire.assert_called_once()
        mock_typer_run.assert_called_once()

    @patch("bot.cli.find_dotenv")
    def test_main_dotenv_not_found_error(self, mock_find_dotenv):
        """Test error handling when .env file is not found"""
        mock_find_dotenv.side_effect = OSError("No .env file found")

        with pytest.raises(OSError, match="No .env file found"):
            main()

    @patch("bot.cli.typer.run")
    @patch("bot.cli.configure_logfire")
    @patch("bot.cli.load_dotenv")
    @patch("bot.cli.find_dotenv")
    def test_main_load_dotenv_failure(self, mock_find_dotenv, mock_load_dotenv, mock_configure_logfire, mock_typer_run):
        """Test error handling when load_dotenv fails"""
        mock_find_dotenv.return_value = ".env"
        mock_load_dotenv.side_effect = Exception("Failed to load .env")

        with pytest.raises(Exception, match="Failed to load .env"):
            main()

        # configure_logfire and typer.run should not be called
        mock_configure_logfire.assert_not_called()
        mock_typer_run.assert_not_called()

    @patch("bot.cli.typer.run")
    @patch("bot.cli.configure_logfire")
    @patch("bot.cli.load_dotenv")
    @patch("bot.cli.find_dotenv")
    def test_main_configure_logfire_failure(
        self, mock_find_dotenv, mock_load_dotenv, mock_configure_logfire, mock_typer_run
    ):
        """Test error handling when configure_logfire fails"""
        mock_find_dotenv.return_value = ".env"
        mock_load_dotenv.return_value = True
        mock_configure_logfire.side_effect = Exception("Logfire configuration failed")

        with pytest.raises(Exception, match="Logfire configuration failed"):
            main()

        # typer.run should not be called
        mock_typer_run.assert_not_called()

    @patch("bot.cli.typer.run")
    @patch("bot.cli.configure_logfire")
    @patch("bot.cli.load_dotenv")
    @patch("bot.cli.find_dotenv")
    def test_main_typer_run_failure(self, mock_find_dotenv, mock_load_dotenv, mock_configure_logfire, mock_typer_run):
        """Test error handling when typer.run fails"""
        mock_find_dotenv.return_value = ".env"
        mock_load_dotenv.return_value = True
        mock_typer_run.side_effect = Exception("Failed to run bot")

        with pytest.raises(Exception, match="Failed to run bot"):
            main()

    @patch("bot.cli.typer.run")
    @patch("bot.cli.configure_logfire")
    @patch("bot.cli.load_dotenv")
    @patch("bot.cli.find_dotenv")
    def test_main_call_sequence(self, mock_find_dotenv, mock_load_dotenv, mock_configure_logfire, mock_typer_run):
        """Test that functions are called in the correct order"""
        mock_find_dotenv.return_value = ".env"
        mock_load_dotenv.return_value = True

        # Create a manager to track call order
        manager = Mock()
        manager.attach_mock(mock_find_dotenv, "find_dotenv")
        manager.attach_mock(mock_load_dotenv, "load_dotenv")
        manager.attach_mock(mock_configure_logfire, "configure_logfire")
        manager.attach_mock(mock_typer_run, "typer_run")

        main()

        # Verify call order
        expected_calls = [
            ("find_dotenv", (), {}),
            ("load_dotenv", (), {}),
            ("configure_logfire", (), {}),
            ("typer_run", (), {}),
        ]

        actual_calls = list(manager.mock_calls)
        assert len(actual_calls) == 4

        # Check that each expected call type was made
        call_names = [call[0] for call in actual_calls]
        expected_names = [call[0] for call in expected_calls]
        assert call_names == expected_names

    @patch("bot.cli.typer.run")
    @patch("bot.cli.configure_logfire")
    @patch("bot.cli.load_dotenv")
    @patch("bot.cli.find_dotenv")
    def test_main_dotenv_parameters(self, mock_find_dotenv, mock_load_dotenv, mock_configure_logfire, mock_typer_run):
        """Test that dotenv functions are called with correct parameters"""
        mock_find_dotenv.return_value = "/path/to/.env"
        mock_load_dotenv.return_value = True

        main()

        # Verify find_dotenv parameters
        mock_find_dotenv.assert_called_once_with(
            raise_error_if_not_found=True,
            usecwd=True,
        )

        # Verify load_dotenv parameters
        mock_load_dotenv.assert_called_once_with(
            "/path/to/.env",
            override=True,
        )

    @patch("bot.cli.typer.run")
    @patch("bot.cli.configure_logfire")
    @patch("bot.cli.load_dotenv")
    @patch("bot.cli.find_dotenv")
    def test_main_no_return_value(self, mock_find_dotenv, mock_load_dotenv, mock_configure_logfire, mock_typer_run):
        """Test that main function returns None"""
        mock_find_dotenv.return_value = ".env"
        mock_load_dotenv.return_value = True

        result = main()

        assert result is None

    @patch("bot.cli.typer")
    @patch("bot.cli.configure_logfire")
    @patch("bot.cli.load_dotenv")
    @patch("bot.cli.find_dotenv")
    def test_main_integration_with_real_imports(
        self, mock_find_dotenv, mock_load_dotenv, mock_configure_logfire, mock_typer
    ):
        """Test integration with real run_bot import"""
        mock_find_dotenv.return_value = ".env"
        mock_load_dotenv.return_value = True
        mock_typer.run = Mock()

        main()

        # Verify that typer.run was called with the actual run_bot function
        mock_typer.run.assert_called_once()

        # Get the argument passed to typer.run
        call_args = mock_typer.run.call_args
        passed_function = call_args[0][0]

        # Import the actual run_bot function to compare
        from bot.bot import run_bot

        assert passed_function == run_bot
