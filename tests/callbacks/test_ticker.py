import json
from typing import cast
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.types import User

from bot.callbacks.ticker import query_ticker_callback


@pytest.fixture
def test_user() -> User:
    return User(id=123, is_bot=False, first_name="TestUser", username="testuser")


def _message(text: str, test_user: User) -> tuple[Message, AsyncMock]:
    message = Mock(spec=Message)
    message.text = text
    message.from_user = test_user
    answer = AsyncMock()
    message.answer = answer
    return cast(Message, message), answer


@pytest.mark.asyncio
async def test_query_ticker_callback_no_args(test_user: User):
    message, _answer = _message("/ticker", test_user)

    result = await query_ticker_callback(message)
    assert result is None


@pytest.mark.asyncio
@patch("bot.callbacks.ticker.query_tickers")
@patch("bot.callbacks.ticker.get_stock_info")
async def test_query_ticker_callback_success(mock_get_stock_info, mock_query_tickers, test_user: User):
    mock_query_tickers.return_value = "Yahoo Finance result for AAPL"

    mock_stock_info = Mock()
    mock_stock_info.pretty_repr.return_value = "TWSE result for AAPL"
    mock_get_stock_info.return_value = mock_stock_info

    message, answer = _message("/ticker AAPL", test_user)

    await query_ticker_callback(message)

    mock_query_tickers.assert_called_once_with(["AAPL"])
    mock_get_stock_info.assert_called_once_with("AAPL")

    expected_result = "Yahoo Finance result for AAPL\n\nTWSE result for AAPL"
    answer.assert_called_once_with(expected_result, parse_mode=ParseMode.MARKDOWN_V2)


@pytest.mark.asyncio
@patch("bot.callbacks.ticker.query_tickers")
@patch("bot.callbacks.ticker.get_stock_info")
async def test_query_ticker_callback_yahoo_finance_error(mock_get_stock_info, mock_query_tickers, test_user: User):
    mock_query_tickers.side_effect = Exception("Yahoo Finance API error")

    mock_stock_info = Mock()
    mock_stock_info.pretty_repr.return_value = "TWSE result for AAPL"
    mock_get_stock_info.return_value = mock_stock_info

    message, answer = _message("/ticker AAPL", test_user)

    await query_ticker_callback(message)

    mock_query_tickers.assert_called_once_with(["AAPL"])
    mock_get_stock_info.assert_called_once_with("AAPL")

    expected_result = "TWSE result for AAPL"
    answer.assert_called_once_with(expected_result, parse_mode=ParseMode.MARKDOWN_V2)


@pytest.mark.asyncio
@patch("bot.callbacks.ticker.query_tickers")
@patch("bot.callbacks.ticker.get_stock_info")
async def test_query_ticker_callback_twse_error(mock_get_stock_info, mock_query_tickers, test_user: User):
    mock_query_tickers.return_value = "Yahoo Finance result for AAPL"
    mock_get_stock_info.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

    message, answer = _message("/ticker AAPL", test_user)

    await query_ticker_callback(message)

    mock_query_tickers.assert_called_once_with(["AAPL"])
    mock_get_stock_info.assert_called_once_with("AAPL")

    expected_result = "Yahoo Finance result for AAPL"
    answer.assert_called_once_with(expected_result, parse_mode=ParseMode.MARKDOWN_V2)


@pytest.mark.asyncio
@patch("bot.callbacks.ticker.query_tickers")
@patch("bot.callbacks.ticker.get_stock_info")
async def test_query_ticker_callback_multiple_symbols(mock_get_stock_info, mock_query_tickers, test_user: User):
    mock_query_tickers.return_value = "Yahoo Finance results"

    mock_stock_info1 = Mock()
    mock_stock_info1.pretty_repr.return_value = "TWSE result for AAPL"
    mock_stock_info2 = Mock()
    mock_stock_info2.pretty_repr.return_value = "TWSE result for GOOGL"

    mock_get_stock_info.side_effect = [mock_stock_info1, mock_stock_info2]

    message, answer = _message("/ticker AAPL GOOGL", test_user)

    await query_ticker_callback(message)

    mock_query_tickers.assert_called_once_with(["AAPL", "GOOGL"])
    assert mock_get_stock_info.call_count == 2

    expected_result = "Yahoo Finance results\n\nTWSE result for AAPL\n\nTWSE result for GOOGL"
    answer.assert_called_once_with(expected_result, parse_mode=ParseMode.MARKDOWN_V2)


@pytest.mark.asyncio
@patch("bot.callbacks.ticker.query_tickers")
@patch("bot.callbacks.ticker.get_stock_info")
async def test_query_ticker_callback_no_results(mock_get_stock_info, mock_query_tickers, test_user: User):
    mock_query_tickers.side_effect = Exception("No data")
    mock_get_stock_info.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

    message, answer = _message("/ticker INVALID", test_user)

    result = await query_ticker_callback(message)

    assert result is None
    answer.assert_called_once()
    call_args = answer.call_args[0][0]
    assert "無法查詢到股票代碼" in call_args
    assert "INVALID" in call_args
