import json
import tempfile
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from bot.utils import create_page
from bot.utils import get_telegraph_client
from bot.utils import load_json
from bot.utils import logfire_is_enabled
from bot.utils import parse_url
from bot.utils import parse_urls
from bot.utils import save_json
from bot.utils import save_text


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Check this out: https://example.com", "https://example.com"),
        ("No URL here!", ""),
        ("Multiple URLs: https://example.com and https://another.com", "https://example.com"),
        ("Just text", ""),
        ("https://domain.com/path?query=1", "https://domain.com/path?query=1"),
        ("Visit http://insecure.com for info", "http://insecure.com"),
        (
            "Text with https://sub.domain.co.uk/path/file.html?a=1&b=2",
            "https://sub.domain.co.uk/path/file.html?a=1&b=2",
        ),
    ],
)
def test_parse_url(text: str, expected: str) -> None:
    result = parse_url(text)
    assert result == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Check this out: https://example.com", ["https://example.com"]),
        ("No URL here!", []),
        ("Multiple URLs: https://example.com and https://another.com", ["https://example.com", "https://another.com"]),
        ("Just text", []),
        ("https://domain.com/path?query=1", ["https://domain.com/path?query=1"]),
        ("Visit http://insecure.com for info", ["http://insecure.com"]),
        (
            "Text with https://sub.domain.co.uk/path/file.html?a=1&b=2",
            ["https://sub.domain.co.uk/path/file.html?a=1&b=2"],
        ),
        (
            "Three URLs: https://first.com https://second.com https://third.com",
            ["https://first.com", "https://second.com", "https://third.com"],
        ),
        (
            "Mixed: http://example.com and https://secure.com text https://another.org",
            ["http://example.com", "https://secure.com", "https://another.org"],
        ),
    ],
)
def test_parse_urls(text: str, expected: list[str]) -> None:
    result = parse_urls(text)
    assert result == expected


class TestUtilsFunctions:
    def test_save_text(self):
        """Test saving text to file"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            temp_path = f.name

        try:
            test_text = "Hello, World!\nThis is a test."
            save_text(test_text, temp_path)

            # Verify file was written correctly
            with open(temp_path) as f:
                content = f.read()
            assert content == test_text
        finally:
            Path(temp_path).unlink()

    def test_load_json_valid_file(self):
        """Test loading valid JSON file"""
        test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name

        try:
            result = load_json(temp_path)
            assert result == test_data
        finally:
            Path(temp_path).unlink()

    def test_load_json_with_path_object(self):
        """Test loading JSON using Path object"""
        test_data = {"test": True}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_path = Path(f.name)

        try:
            result = load_json(temp_path)
            assert result == test_data
        finally:
            temp_path.unlink()

    def test_load_json_invalid_extension(self):
        """Test error when file doesn't have .json extension"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="is not a json file"):
                load_json(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_json_invalid_content(self):
        """Test error when file contains invalid JSON"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            temp_path = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                load_json(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_save_json(self):
        """Test saving data to JSON file"""
        test_data = {"key": "value", "number": 42, "nested": {"a": 1}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save_json(test_data, temp_path)

            # Verify file was written correctly
            with open(temp_path, encoding="utf-8") as f:
                content = f.read()
                loaded_data = json.loads(content)

            assert loaded_data == test_data
            # Check formatting (should be indented)
            assert "    " in content  # Should have indentation
        finally:
            Path(temp_path).unlink()

    @patch("bot.utils.telegraph.Telegraph")
    def test_get_telegraph_client(self, mock_telegraph_class):
        """Test telegraph client creation"""
        mock_client = Mock()
        mock_telegraph_class.return_value = mock_client

        client = get_telegraph_client()

        mock_telegraph_class.assert_called_once()
        assert client == mock_client

    @patch("bot.utils.get_telegraph_client")
    def test_create_page_success(self, mock_get_client):
        """Test successful page creation"""
        mock_client = Mock()
        mock_client.create_page.return_value = {"url": "https://telegra.ph/test-page"}
        mock_get_client.return_value = mock_client

        result = create_page(title="Test Title", content="Test content")

        mock_client.create_page.assert_called_once_with(title="Test Title", content="Test content")
        assert result == "https://telegra.ph/test-page"

    @patch("bot.utils.get_telegraph_client")
    def test_create_page_failure(self, mock_get_client):
        """Test page creation failure"""
        mock_client = Mock()
        mock_client.create_page.side_effect = Exception("API Error")
        mock_get_client.return_value = mock_client

        # This should raise an exception since create_page doesn't handle errors
        with pytest.raises((Exception, RuntimeError, ValueError)):
            create_page(title="Test Title", content="Test content")

    def test_logfire_is_enabled_with_token(self):
        """Test logfire detection when token is set"""
        with patch.dict("os.environ", {"LOGFIRE_TOKEN": "test_token"}):
            assert logfire_is_enabled() is True

    def test_logfire_is_enabled_without_token(self):
        """Test logfire detection when token is not set"""
        with patch.dict("os.environ", {}, clear=True):
            assert logfire_is_enabled() is False

    def test_logfire_is_enabled_empty_token(self):
        """Test logfire detection when token is empty"""
        with patch.dict("os.environ", {"LOGFIRE_TOKEN": ""}):
            assert logfire_is_enabled() is False

    @patch("bot.utils.logfire_is_enabled")
    @patch("bot.utils.logfire")
    @patch("bot.utils.logger")
    def test_configure_logfire_enabled(self, mock_logger, mock_logfire, mock_is_enabled):
        """Test logfire configuration when enabled"""
        mock_is_enabled.return_value = True
        mock_logfire.loguru_handler.return_value = Mock()

        from bot.utils import configure_logfire

        configure_logfire()

        mock_logfire.configure.assert_called_once()
        mock_logfire.instrument_openai_agents.assert_called_once()
        mock_logger.configure.assert_called_once()

    @patch("bot.utils.logfire_is_enabled")
    @patch("bot.utils.logfire")
    def test_configure_logfire_disabled(self, mock_logfire, mock_is_enabled):
        """Test logfire configuration when disabled"""
        mock_is_enabled.return_value = False

        from bot.utils import configure_logfire

        configure_logfire()

        mock_logfire.configure.assert_not_called()

    @patch.dict(
        "os.environ",
        {
            "LANGFUSE_PUBLIC_KEY": "test_key",
            "LANGFUSE_SECRET_KEY": "test_secret",
            "LANGFUSE_HOST": "https://cloud.langfuse.com",
        },
    )
    @patch("bot.utils.logfire")
    @patch("bot.utils.nest_asyncio")
    @patch("bot.utils.logger")
    def test_configure_langfuse_with_keys(self, mock_logger, mock_nest_asyncio, mock_logfire):
        """Test langfuse configuration when keys are available"""
        mock_logfire.loguru_handler.return_value = Mock()

        from bot.utils import configure_langfuse

        configure_langfuse("test_service")

        # Should configure logfire when keys are present
        mock_logfire.configure.assert_called_once()
        mock_nest_asyncio.apply.assert_called_once()
        mock_logger.configure.assert_called_once()

    @patch.dict("os.environ", {}, clear=True)
    @patch("bot.utils.logfire")
    def test_configure_langfuse_without_keys(self, mock_logfire):
        """Test langfuse configuration when keys are missing"""
        from bot.utils import configure_langfuse

        configure_langfuse("test_service")

        # Should not configure logfire when keys are missing
        mock_logfire.configure.assert_not_called()
