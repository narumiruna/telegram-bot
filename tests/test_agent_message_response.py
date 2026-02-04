from unittest.mock import AsyncMock
from unittest.mock import Mock

import pytest

from bot.core.message_response import MessageResponse


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
