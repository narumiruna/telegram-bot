from unittest.mock import AsyncMock
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_message_with_reply():
    mock_message = Mock()
    mock_new_message = Mock()
    mock_message.reply_text = AsyncMock(return_value=mock_new_message)
    return mock_message, mock_new_message
