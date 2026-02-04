from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from bot.core.presentation import MessageResponse


@pytest.fixture
def mock_message_with_reply():
    mock_message = Mock()
    mock_new_message = Mock()
    mock_message.reply_text = AsyncMock(return_value=mock_new_message)
    return mock_message, mock_new_message


@pytest.mark.asyncio
async def test_message_response_short_content(mock_message_with_reply):
    """Test MessageResponse with short content."""
    response = MessageResponse(content="Short response", title="Test", parse_mode="HTML")
    mock_message, mock_new_message = mock_message_with_reply

    # Send response
    result = await response.send(mock_message)

    # Should send directly for short content
    mock_message.reply_text.assert_called_once_with("Short response", parse_mode="HTML")
    assert result == mock_new_message


@pytest.mark.asyncio
@patch("bot.core.presentation.async_create_page")
async def test_message_response_long_content(mock_create_page, mock_message_with_reply):
    """Test MessageResponse with long content triggers Telegraph."""
    from bot.settings import settings

    long_content = "A" * (settings.max_message_length + 100)
    response = MessageResponse(content=long_content, title="Long Response", parse_mode="HTML")

    # Mock message and Telegraph
    mock_message, mock_new_message = mock_message_with_reply
    mock_create_page.return_value = "https://telegra.ph/test-page"

    # Send response
    result = await response.send(mock_message)

    # Should create Telegraph page for long content
    mock_create_page.assert_called_once()
    create_args = mock_create_page.call_args
    assert create_args[1]["title"] == "Long Response"
    assert long_content in create_args[1]["html_content"]

    # Should send Telegraph URL
    mock_message.reply_text.assert_called_once_with("https://telegra.ph/test-page")
    assert result == mock_new_message
