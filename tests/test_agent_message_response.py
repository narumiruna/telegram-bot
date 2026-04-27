from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest

import bot.core.message_response as message_response_module
from bot.agents.writer import Article
from bot.agents.writer import Section
from bot.core.message_response import MessageResponse


@pytest.fixture
def mock_message():
    message = Mock()
    sent_message = Mock()
    message.reply = AsyncMock(return_value=sent_message)
    return message, sent_message


@pytest.mark.asyncio
async def test_message_response_reply_uses_message_reply(mock_message):
    message, sent_message = mock_message
    response = MessageResponse(content="Hello")

    result = await response.reply(message)

    assert result is sent_message
    message.reply.assert_called_once_with(
        "Hello",
        parse_mode="HTML",
        allow_sending_without_reply=True,
    )


@pytest.mark.asyncio
@patch("bot.core.message_response.async_create_page", new_callable=AsyncMock)
async def test_message_response_reply_long_content_uses_message_reply(mock_create_page, mock_message):
    message, sent_message = mock_message
    mock_create_page.return_value = "https://example.com/page"
    response = MessageResponse(content="abcd")

    with patch.object(message_response_module.settings, "max_message_length", 3):
        result = await response.reply(message)

    assert result is sent_message
    mock_create_page.assert_awaited_once_with(title="Response", html_content="abcd")
    message.reply.assert_called_once_with(
        "https://example.com/page",
        allow_sending_without_reply=True,
    )


@pytest.mark.asyncio
@patch.object(Article, "create_page", new_callable=AsyncMock)
async def test_article_reply_uses_message_reply(mock_create_page, mock_message):
    message, sent_message = mock_message
    mock_create_page.return_value = "https://example.com/article"
    article = Article(
        title="測試文章",
        summary="摘要",
        sections=[Section(title="段落", emoji="📝", content="內容")],
    )

    result = await article.reply(message)

    assert result is sent_message
    message.reply.assert_called_once_with(
        "https://example.com/article",
        parse_mode="HTML",
        allow_sending_without_reply=True,
    )
