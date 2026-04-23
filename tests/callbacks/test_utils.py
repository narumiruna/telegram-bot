from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from aiogram.types import Message
from aiogram.types import User

from bot.callbacks.utils import get_message_key
from bot.callbacks.utils import get_message_text
from bot.callbacks.utils import get_processed_message_text
from bot.callbacks.utils import get_user_display_name
from bot.callbacks.utils import safe_callback
from bot.callbacks.utils import strip_command


@pytest.fixture
def test_user() -> User:
    return User(id=123, is_bot=False, first_name="TestUser", username="testuser")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("/sum 1 2 3", "1 2 3"),
        ("/start", ""),
        ("hello", "hello"),
        ("/command with multiple words", "with multiple words"),
        ("/", ""),
        ("/cmd", ""),
        ("/cmd ", ""),
        ("/cmd  multiple  spaces", " multiple  spaces"),
    ],
)
def test_strip_command(text, expected):
    assert strip_command(text) == expected


def test_get_user_display_name_with_username():
    user = User(id=123, is_bot=False, first_name="なるみ", username="narumi")
    message = Mock(spec=Message)
    message.from_user = user

    result = get_user_display_name(message)
    assert result == "なるみ(narumi)"


def test_get_user_display_name_without_username():
    user = User(id=123, is_bot=False, first_name="なるみ")
    message = Mock(spec=Message)
    message.from_user = user

    result = get_user_display_name(message)
    assert result == "なるみ"


def test_get_user_display_name_no_user():
    message = Mock(spec=Message)
    message.from_user = None

    result = get_user_display_name(message)
    assert result is None


def test_get_message_text_simple(test_user: User):
    message = Mock(spec=Message)
    message.text = "Hello world"
    message.caption = None
    message.from_user = test_user
    message.reply_to_message = None

    result = get_message_text(message)
    assert result == "Hello world"


def test_get_message_text_with_command(test_user: User):
    message = Mock(spec=Message)
    message.text = "/translate Hello world"
    message.caption = None
    message.from_user = test_user
    message.reply_to_message = None

    result = get_message_text(message)
    assert result == "Hello world"


def test_get_message_text_with_user_name(test_user: User):
    message = Mock(spec=Message)
    message.text = "Hello world"
    message.caption = None
    message.from_user = test_user
    message.reply_to_message = None

    result = get_message_text(message, include_user_name=True)
    assert result == "TestUser(testuser): Hello world"


def test_get_message_text_with_reply(test_user: User):
    reply_message = Mock(spec=Message)
    reply_message.text = "Original message"
    reply_message.caption = None
    reply_message.from_user = test_user
    reply_message.reply_to_message = None

    message = Mock(spec=Message)
    message.text = "Reply message"
    message.caption = None
    message.from_user = test_user
    message.reply_to_message = reply_message

    result = get_message_text(message)
    assert result == "Original message\n\nReply message"


def test_get_message_text_empty(test_user: User):
    message = Mock(spec=Message)
    message.text = None
    message.caption = None
    message.from_user = test_user
    message.reply_to_message = None

    result = get_message_text(message)
    assert result == ""


def test_get_message_key():
    message = Mock(spec=Message)
    message.message_id = 123
    message.chat = Mock()
    message.chat.id = 456

    result = get_message_key(message)
    assert result == "123:456"


@pytest.mark.asyncio
async def test_no_message_text(test_user: User):
    message = Mock(spec=Message)
    message.text = ""
    message.caption = None
    message.from_user = test_user
    message.reply_to_message = None

    text, error = await get_processed_message_text(message, require_url=False)
    assert text is None
    assert error is None


@pytest.mark.asyncio
@patch("bot.callbacks.utils.parse_urls")
async def test_require_url_but_no_url(mock_parse_urls, test_user: User):
    mock_parse_urls.return_value = []

    message = Mock(spec=Message)
    message.text = "No URL here"
    message.caption = None
    message.from_user = test_user
    message.reply_to_message = None

    text, error = await get_processed_message_text(message, require_url=True)
    assert text is None
    assert error is None


@pytest.mark.asyncio
@patch("bot.callbacks.utils.parse_urls")
async def test_no_url_returns_original_text(mock_parse_urls, test_user: User):
    mock_parse_urls.return_value = []

    message = Mock(spec=Message)
    message.text = "No URL here"
    message.caption = None
    message.from_user = test_user
    message.reply_to_message = None

    text, error = await get_processed_message_text(message, require_url=False)
    assert text == "No URL here"
    assert error is None


@pytest.mark.asyncio
@patch("bot.callbacks.utils.load_url")
@patch("bot.callbacks.utils.parse_urls")
async def test_url_loading_success(mock_parse_urls, mock_load_url, test_user: User):
    mock_parse_urls.return_value = ["https://example.com"]
    mock_load_url.return_value = "Content from URL"

    message = Mock(spec=Message)
    message.text = "https://example.com"
    message.caption = None
    message.from_user = test_user
    message.reply_to_message = None

    text, error = await get_processed_message_text(message, require_url=False)
    assert text == "https://example.com\n\nURL content from https://example.com:\nContent from URL"
    assert error is None
    mock_load_url.assert_called_once_with("https://example.com")


@pytest.mark.asyncio
@patch("bot.callbacks.utils.load_url")
@patch("bot.callbacks.utils.parse_urls")
async def test_url_loading_failure(mock_parse_urls, mock_load_url, test_user: User):
    mock_parse_urls.return_value = ["https://example.com"]
    mock_load_url.side_effect = Exception("Connection error")

    message = Mock(spec=Message)
    message.text = "https://example.com"
    message.caption = None
    message.from_user = test_user
    message.reply_to_message = None

    text, error = await get_processed_message_text(message, require_url=False)
    assert text is None
    assert error == "Failed to load URL(s): https://example.com"


@pytest.mark.asyncio
@patch("bot.callbacks.utils.load_url")
@patch("bot.callbacks.utils.parse_urls")
async def test_require_url_with_url_success(mock_parse_urls, mock_load_url, test_user: User):
    mock_parse_urls.return_value = ["https://example.com"]
    mock_load_url.return_value = "Content from URL"

    message = Mock(spec=Message)
    message.text = "https://example.com"
    message.caption = None
    message.from_user = test_user
    message.reply_to_message = None

    text, error = await get_processed_message_text(message, require_url=True)
    assert text == "https://example.com\n\nURL content from https://example.com:\nContent from URL"
    assert error is None
    mock_load_url.assert_called_once_with("https://example.com")


@pytest.mark.asyncio
@patch("bot.callbacks.utils.load_url")
@patch("bot.callbacks.utils.parse_urls")
async def test_multiple_urls_loading_success(mock_parse_urls, mock_load_url, test_user: User):
    mock_parse_urls.return_value = ["https://example1.com", "https://example2.com"]
    mock_load_url.side_effect = ["Content from URL 1", "Content from URL 2"]

    message = Mock(spec=Message)
    message.text = "Check https://example1.com and https://example2.com"
    message.caption = None
    message.from_user = test_user
    message.reply_to_message = None

    text, error = await get_processed_message_text(message, require_url=False)
    assert text == (
        "Check https://example1.com and https://example2.com\n\n"
        "URL content from https://example1.com:\nContent from URL 1\n\n"
        "URL content from https://example2.com:\nContent from URL 2"
    )
    assert error is None
    assert mock_load_url.call_count == 2


@pytest.mark.asyncio
@patch("bot.callbacks.utils.load_url")
@patch("bot.callbacks.utils.parse_urls")
async def test_multiple_urls_one_fails(mock_parse_urls, mock_load_url, test_user: User):
    mock_parse_urls.return_value = ["https://example1.com", "https://example2.com"]
    mock_load_url.side_effect = Exception("Connection error")

    message = Mock(spec=Message)
    message.text = "Check https://example1.com and https://example2.com"
    message.caption = None
    message.from_user = test_user
    message.reply_to_message = None

    text, error = await get_processed_message_text(message, require_url=False)
    assert text is None
    assert error == "Failed to load URL(s): https://example1.com, https://example2.com"


@pytest.mark.asyncio
@patch("bot.callbacks.utils.load_url")
@patch("bot.callbacks.utils.parse_urls")
async def test_multiple_urls_require_url(mock_parse_urls, mock_load_url, test_user: User):
    mock_parse_urls.return_value = ["https://example1.com", "https://example2.com", "https://example3.com"]
    mock_load_url.side_effect = ["Content 1", "Content 2", "Content 3"]

    message = Mock(spec=Message)
    message.text = "Three URLs: https://example1.com https://example2.com https://example3.com"
    message.caption = None
    message.from_user = test_user
    message.reply_to_message = None

    text, error = await get_processed_message_text(message, require_url=True)
    assert text == (
        "Three URLs: https://example1.com https://example2.com https://example3.com\n\n"
        "URL content from https://example1.com:\nContent 1\n\n"
        "URL content from https://example2.com:\nContent 2\n\n"
        "URL content from https://example3.com:\nContent 3"
    )
    assert error is None
    assert mock_load_url.call_count == 3


@pytest.mark.asyncio
@patch("bot.callbacks.utils.parse_urls")
async def test_include_reply_to_message_true_includes_reply_text(mock_parse_urls, test_user: User):
    mock_parse_urls.return_value = []

    reply_message = Mock(spec=Message)
    reply_message.text = "Original message"
    reply_message.caption = None
    reply_message.from_user = test_user
    reply_message.reply_to_message = None

    message = Mock(spec=Message)
    message.text = "Reply message"
    message.caption = None
    message.from_user = test_user
    message.reply_to_message = reply_message

    text, error = await get_processed_message_text(
        message,
        require_url=False,
        include_reply_to_message=True,
    )

    assert text == "Replied message:\nOriginal message\n\nCurrent message:\nReply message"
    assert error is None
    mock_parse_urls.assert_called_once_with("Replied message:\nOriginal message\n\nCurrent message:\nReply message")


@pytest.mark.asyncio
@patch("bot.callbacks.utils.load_url")
@patch("bot.callbacks.utils.parse_urls")
async def test_reply_message_with_current_url_keeps_sections(
    mock_parse_urls,
    mock_load_url,
    test_user: User,
):
    mock_parse_urls.return_value = ["https://example.com"]
    mock_load_url.return_value = "Loaded page"

    reply_message = Mock(spec=Message)
    reply_message.text = "Bot said hello"
    reply_message.caption = None
    reply_message.from_user = test_user
    reply_message.reply_to_message = None

    message = Mock(spec=Message)
    message.text = "Please summarize https://example.com"
    message.caption = None
    message.from_user = test_user
    message.reply_to_message = reply_message

    text, error = await get_processed_message_text(message, require_url=False, include_reply_to_message=True)

    assert text == (
        "Replied message:\nBot said hello\n\n"
        "Current message:\nPlease summarize https://example.com\n\n"
        "URL content from https://example.com:\nLoaded page"
    )
    assert error is None


@pytest.mark.asyncio
@patch("bot.callbacks.utils.load_url")
@patch("bot.callbacks.utils.parse_urls")
async def test_reply_message_with_reply_url_keeps_original_sections(mock_parse_urls, mock_load_url, test_user: User):
    mock_parse_urls.return_value = ["https://example.com"]
    mock_load_url.return_value = "Loaded page"

    reply_message = Mock(spec=Message)
    reply_message.text = "Context https://example.com"
    reply_message.caption = None
    reply_message.from_user = test_user
    reply_message.reply_to_message = None

    message = Mock(spec=Message)
    message.text = "What does this mean?"
    message.caption = None
    message.from_user = test_user
    message.reply_to_message = reply_message

    text, error = await get_processed_message_text(message, require_url=False, include_reply_to_message=True)

    assert text == (
        "Replied message:\nContext https://example.com\n\n"
        "Current message:\nWhat does this mean?\n\n"
        "URL content from https://example.com:\nLoaded page"
    )
    assert error is None


@pytest.mark.asyncio
@patch("bot.callbacks.utils.parse_urls")
async def test_include_reply_to_message_false_excludes_reply_text(mock_parse_urls, test_user: User):
    mock_parse_urls.return_value = []

    reply_message = Mock(spec=Message)
    reply_message.text = "Original message"
    reply_message.caption = None
    reply_message.from_user = test_user
    reply_message.reply_to_message = None

    message = Mock(spec=Message)
    message.text = "Reply message"
    message.caption = None
    message.from_user = test_user
    message.reply_to_message = reply_message

    text, error = await get_processed_message_text(
        message,
        require_url=False,
        include_reply_to_message=False,
    )

    assert text == "Reply message"
    assert error is None
    mock_parse_urls.assert_called_once_with("Reply message")


@pytest.mark.asyncio
async def test_safe_callback_normal_execution():
    mock_message = Mock(spec=Message)

    @safe_callback
    async def test_callback(message):
        return "success"

    result = await test_callback(mock_message)
    assert result == "success"


@pytest.mark.asyncio
async def test_safe_callback_exception_handling():
    mock_message = Mock(spec=Message)
    mock_message.answer = AsyncMock()

    @safe_callback
    async def test_callback(message):
        raise ValueError("Test error")

    with pytest.raises(ValueError):
        await test_callback(mock_message)

    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args[0][0]
    assert "抱歉" in call_args
    assert "錯誤" in call_args


@pytest.mark.asyncio
async def test_safe_callback_answer_fails():
    mock_message = Mock(spec=Message)
    mock_message.answer = AsyncMock(side_effect=Exception("Reply failed"))

    @safe_callback
    async def test_callback(message):
        raise ValueError("Test error")

    with pytest.raises(ValueError):
        await test_callback(mock_message)

    mock_message.answer.assert_called_once()
