import html
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from telegram import Message

from bot.presentation import MessageResponse


class TestMessageResponse:
    @pytest.mark.asyncio
    async def test_send_short_message(self):
        """Test sending a short message directly"""
        content = "This is a short message"
        response = MessageResponse(content=content, title="Test")

        message = Mock(spec=Message)
        message.reply_text = AsyncMock()

        await response.send(message)

        message.reply_text.assert_called_once_with(content, parse_mode="HTML")

    @pytest.mark.asyncio
    async def test_send_short_message_without_parse_mode(self):
        """Test sending a short plain text message"""
        content = "This is plain text"
        response = MessageResponse(content=content, parse_mode=None)

        message = Mock(spec=Message)
        message.reply_text = AsyncMock()

        await response.send(message)

        message.reply_text.assert_called_once_with(content, parse_mode=None)

    @pytest.mark.asyncio
    @patch("bot.presentation.async_create_page")
    async def test_send_long_message_creates_telegraph_page(self, mock_create_page):
        """Test that long messages create a Telegraph page"""
        # Create a message longer than MAX_MESSAGE_LENGTH (1000 characters)
        content = "x" * 1001
        response = MessageResponse(content=content, title="Long Message")

        mock_create_page.return_value = "https://telegra.ph/test-page"

        message = Mock(spec=Message)
        message.reply_text = AsyncMock()

        await response.send(message)

        # Should create Telegraph page
        mock_create_page.assert_called_once_with(
            title="Long Message",
            html_content=content.replace("\n", "<br>"),
        )

        # Should send the Telegraph URL
        message.reply_text.assert_called_once_with("https://telegra.ph/test-page")

    @pytest.mark.asyncio
    @patch("bot.presentation.async_create_page")
    async def test_send_long_message_with_default_title(self, mock_create_page):
        """Test that long messages use default title if not provided"""
        content = "y" * 1001
        response = MessageResponse(content=content)  # No title specified

        mock_create_page.return_value = "https://telegra.ph/response"

        message = Mock(spec=Message)
        message.reply_text = AsyncMock()

        await response.send(message)

        # Should use "Response" as default title
        mock_create_page.assert_called_once_with(
            title="Response",
            html_content=content.replace("\n", "<br>"),
        )

    @pytest.mark.asyncio
    @patch("bot.presentation.async_create_page")
    async def test_send_exactly_max_length_message(self, mock_create_page):
        """Test message exactly at MAX_MESSAGE_LENGTH (1000 chars) sends directly"""
        content = "z" * 1000  # Exactly at the limit
        response = MessageResponse(content=content)

        message = Mock(spec=Message)
        message.reply_text = AsyncMock()

        await response.send(message)

        # Should NOT create Telegraph page (limit is exclusive)
        mock_create_page.assert_not_called()

        # Should send directly
        message.reply_text.assert_called_once_with(content, parse_mode="HTML")

    @pytest.mark.asyncio
    @patch("bot.presentation.async_create_page")
    async def test_newlines_converted_to_br_tags(self, mock_create_page):
        """Test that newlines are converted to <br> tags in Telegraph pages"""
        content = "Line 1\nLine 2\nLine 3\n" * 300  # Make it long enough
        response = MessageResponse(content=content, title="Multiline")

        mock_create_page.return_value = "https://telegra.ph/multiline"

        message = Mock(spec=Message)
        message.reply_text = AsyncMock()

        await response.send(message)

        # Verify newlines are replaced with <br>
        expected_html = content.replace("\n", "<br>")
        mock_create_page.assert_called_once_with(
            title="Multiline",
            html_content=expected_html,
        )

    @pytest.mark.asyncio
    @patch("bot.presentation.async_create_page")
    async def test_send_long_plain_text_escapes_html(self, mock_create_page):
        """Test that long plain text is HTML-escaped for Telegraph pages"""
        content = ("<promise>foo</promise>\n" * 200) + ("x" * 1001)
        response = MessageResponse(content=content, title="Plain", parse_mode=None)

        mock_create_page.return_value = "https://telegra.ph/plain"

        message = Mock(spec=Message)
        message.reply_text = AsyncMock()

        await response.send(message)

        mock_create_page.assert_called_once_with(
            title="Plain",
            html_content=html.escape(content).replace("\n", "<br>"),
        )
        message.reply_text.assert_called_once_with("https://telegra.ph/plain")
