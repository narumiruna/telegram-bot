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


# Note: Tests for call sequence, no return value, and integration removed per CONSTITUTION.md §40.
# Those tests only validated mock call patterns without testing real CLI behavior.
