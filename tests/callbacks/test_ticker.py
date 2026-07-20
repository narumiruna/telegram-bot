import json
from typing import cast
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.types import User
from twse.stock_info import StockInfo

from bot.callbacks.ticker import _query_twse
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


def _stock_response(symbol: str, name: str) -> tuple[Mock, str]:
    stock = StockInfo.model_validate(
        {"c": symbol, "n": name, "o": 100, "h": 110, "l": 90, "z": 105, "y": 100, "v": 1000, "ex": "tse"}
    )
    return Mock(msg_array=[stock]), stock.pretty_repr()


@pytest.mark.asyncio
async def test_query_ticker_callback_no_args(test_user: User):
    message, _answer = _message("/ticker", test_user)

    result = await query_ticker_callback(message)
    assert result is None


@pytest.mark.asyncio
@patch("bot.callbacks.ticker.get_stock_info")
async def test_query_twse_escapes_markdown_in_stock_name(mock_get_stock_info):
    stock = StockInfo.model_validate(
        {"c": "2327", "n": "國巨*", "o": 663, "h": 666, "l": 630, "z": 630, "y": 699, "v": 30727, "ex": "tse"}
    )
    response = Mock(msg_array=[stock])
    mock_get_stock_info.return_value = response

    result = await _query_twse(["2327"])

    assert result[0].startswith("📊 *國巨\\* \\(2327\\)*")


@pytest.mark.asyncio
@patch("bot.callbacks.ticker.query_tickers")
@patch("bot.callbacks.ticker.get_stock_info")
async def test_query_ticker_callback_success(mock_get_stock_info, mock_query_tickers, test_user: User):
    mock_query_tickers.return_value = "Yahoo Finance result for AAPL"

    mock_stock_info, twse_result = _stock_response("AAPL", "AAPL Taiwan")
    mock_get_stock_info.return_value = mock_stock_info

    message, answer = _message("/ticker AAPL", test_user)

    await query_ticker_callback(message)

    mock_query_tickers.assert_called_once_with(["AAPL"])
    mock_get_stock_info.assert_called_once_with("AAPL")

    expected_result = f"Yahoo Finance result for AAPL\n\n{twse_result}"
    answer.assert_called_once_with(expected_result, parse_mode=ParseMode.MARKDOWN_V2)


@pytest.mark.asyncio
@patch("bot.callbacks.ticker.query_tickers")
@patch("bot.callbacks.ticker.get_stock_info")
async def test_query_ticker_callback_yahoo_finance_error(mock_get_stock_info, mock_query_tickers, test_user: User):
    mock_query_tickers.side_effect = Exception("Yahoo Finance API error")

    mock_stock_info, twse_result = _stock_response("AAPL", "AAPL Taiwan")
    mock_get_stock_info.return_value = mock_stock_info

    message, answer = _message("/ticker AAPL", test_user)

    await query_ticker_callback(message)

    mock_query_tickers.assert_called_once_with(["AAPL"])
    mock_get_stock_info.assert_called_once_with("AAPL")

    expected_result = twse_result
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

    mock_stock_info1, twse_result1 = _stock_response("AAPL", "AAPL Taiwan")
    mock_stock_info2, twse_result2 = _stock_response("GOOGL", "GOOGL Taiwan")

    mock_get_stock_info.side_effect = [mock_stock_info1, mock_stock_info2]

    message, answer = _message("/ticker AAPL GOOGL", test_user)

    await query_ticker_callback(message)

    mock_query_tickers.assert_called_once_with(["AAPL", "GOOGL"])
    assert mock_get_stock_info.call_count == 2

    expected_result = f"Yahoo Finance results\n\n{twse_result1}\n\n{twse_result2}"
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
