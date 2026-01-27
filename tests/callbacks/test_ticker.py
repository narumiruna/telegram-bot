import json
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from aiogram.types import Chat
from aiogram.types import Message
from aiogram.types import Update
from aiogram.types import User


from bot.callbacks.ticker import query_ticker_callback


class TestQueryTickerCallback:
    def setup_method(self):
        self.user = User(id=123, is_bot=False, first_name="TestUser", username="testuser")
        self.chat = Chat(id=456, type="private")

    @pytest.mark.asyncio
    async def test_query_ticker_callback_no_message(self):
        update = Mock(spec=Update)
        update.message = None
        context = Mock()

        result = await query_ticker_callback(update, context)
        assert result is None

    @pytest.mark.asyncio
    async def test_query_ticker_callback_no_args(self):
        message = Mock(spec=Message)
        message.text = "/ticker"
        message.from_user = self.user

        update = Mock(spec=Update)
        update.message = message

        context = Mock()
        context.args = []

        result = await query_ticker_callback(update, context)
        assert result is None

    @pytest.mark.asyncio
    @patch("bot.callbacks.ticker.query_tickers")
    @patch("bot.callbacks.ticker.get_stock_info")
    async def test_query_ticker_callback_success(self, mock_get_stock_info, mock_query_tickers):
        mock_query_tickers.return_value = "Yahoo Finance result for AAPL"

        mock_stock_info = Mock()
        mock_stock_info.pretty_repr.return_value = "TWSE result for AAPL"
        mock_get_stock_info.return_value = mock_stock_info

        message = Mock(spec=Message)
        message.text = "/ticker AAPL"
        message.from_user = self.user
        message.answer = AsyncMock()

        update = Mock(spec=Update)
        update.message = message

        context = Mock()
        context.args = ["AAPL"]

        await query_ticker_callback(update, context)

        mock_query_tickers.assert_called_once_with(["AAPL"])
        mock_get_stock_info.assert_called_once_with("AAPL")

        expected_result = "Yahoo Finance result for AAPL\n\nTWSE result for AAPL"
        message.answer.assert_called_once_with(expected_result, parse_mode=ParseMode.MARKDOWN_V2)

    @pytest.mark.asyncio
    @patch("bot.callbacks.ticker.query_tickers")
    @patch("bot.callbacks.ticker.get_stock_info")
    async def test_query_ticker_callback_yahoo_finance_error(self, mock_get_stock_info, mock_query_tickers):
        mock_query_tickers.side_effect = Exception("Yahoo Finance API error")

        mock_stock_info = Mock()
        mock_stock_info.pretty_repr.return_value = "TWSE result for AAPL"
        mock_get_stock_info.return_value = mock_stock_info

        message = Mock(spec=Message)
        message.text = "/ticker AAPL"
        message.from_user = self.user
        message.answer = AsyncMock()

        update = Mock(spec=Update)
        update.message = message

        context = Mock()
        context.args = ["AAPL"]

        await query_ticker_callback(update, context)

        mock_query_tickers.assert_called_once_with(["AAPL"])
        mock_get_stock_info.assert_called_once_with("AAPL")

        expected_result = "TWSE result for AAPL"
        message.answer.assert_called_once_with(expected_result, parse_mode=ParseMode.MARKDOWN_V2)

    @pytest.mark.asyncio
    @patch("bot.callbacks.ticker.query_tickers")
    @patch("bot.callbacks.ticker.get_stock_info")
    async def test_query_ticker_callback_twse_error(self, mock_get_stock_info, mock_query_tickers):
        mock_query_tickers.return_value = "Yahoo Finance result for AAPL"
        mock_get_stock_info.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        message = Mock(spec=Message)
        message.text = "/ticker AAPL"
        message.from_user = self.user
        message.answer = AsyncMock()

        update = Mock(spec=Update)
        update.message = message

        context = Mock()
        context.args = ["AAPL"]

        await query_ticker_callback(update, context)

        mock_query_tickers.assert_called_once_with(["AAPL"])
        mock_get_stock_info.assert_called_once_with("AAPL")

        expected_result = "Yahoo Finance result for AAPL"
        message.answer.assert_called_once_with(expected_result, parse_mode=ParseMode.MARKDOWN_V2)

    @pytest.mark.asyncio
    @patch("bot.callbacks.ticker.query_tickers")
    @patch("bot.callbacks.ticker.get_stock_info")
    async def test_query_ticker_callback_multiple_symbols(self, mock_get_stock_info, mock_query_tickers):
        mock_query_tickers.return_value = "Yahoo Finance results"

        mock_stock_info1 = Mock()
        mock_stock_info1.pretty_repr.return_value = "TWSE result for AAPL"
        mock_stock_info2 = Mock()
        mock_stock_info2.pretty_repr.return_value = "TWSE result for GOOGL"

        mock_get_stock_info.side_effect = [mock_stock_info1, mock_stock_info2]

        message = Mock(spec=Message)
        message.text = "/ticker AAPL GOOGL"
        message.from_user = self.user
        message.answer = AsyncMock()

        update = Mock(spec=Update)
        update.message = message

        context = Mock()
        context.args = ["AAPL", "GOOGL"]

        await query_ticker_callback(update, context)

        mock_query_tickers.assert_called_once_with(["AAPL", "GOOGL"])
        assert mock_get_stock_info.call_count == 2

        expected_result = "Yahoo Finance results\n\nTWSE result for AAPL\n\nTWSE result for GOOGL"
        message.answer.assert_called_once_with(expected_result, parse_mode=ParseMode.MARKDOWN_V2)

    @pytest.mark.asyncio
    @patch("bot.callbacks.ticker.query_tickers")
    @patch("bot.callbacks.ticker.get_stock_info")
    async def test_query_ticker_callback_no_results(self, mock_get_stock_info, mock_query_tickers):
        mock_query_tickers.side_effect = Exception("No data")
        mock_get_stock_info.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        message = Mock(spec=Message)
        message.text = "/ticker INVALID"
        message.from_user = self.user
        message.answer = AsyncMock()

        update = Mock(spec=Update)
        update.message = message

        context = Mock()
        context.args = ["INVALID"]

        result = await query_ticker_callback(update, context)

        assert result is None
        # Should notify user that no results were found
        message.answer.assert_called_once()
        call_args = message.answer.call_args[0][0]
        assert "無法查詢到股票代碼" in call_args
        assert "INVALID" in call_args
