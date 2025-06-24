from unittest.mock import Mock
from unittest.mock import patch

from bot.yahoo_finance import query_tickers


@patch("bot.yahoo_finance.yf.Ticker")
def test_query_tickers(mock_ticker_class):
    # Create a mock ticker object
    mock_ticker = Mock()
    mock_ticker.ticker = "AAPL"
    mock_ticker.info = {
        "symbol": "AAPL",
        "shortName": "Apple Inc.",
        "open": 150.0,
        "dayHigh": 155.0,
        "dayLow": 148.0,
        "currentPrice": 152.0,
        "previousClose": 150.0,
        "fiftyTwoWeekLow": 120.0,
        "fiftyTwoWeekHigh": 180.0,
        "ask": 152.1,
        "bid": 151.9,
        "volume": 1000000,
    }

    # Configure the mock to return our mock ticker
    mock_ticker_class.return_value = mock_ticker

    # Test the function
    result = query_tickers("AAPL")

    # Verify the result contains expected information
    assert "AAPL" in result
    assert "Apple Inc" in result  # Note: periods are escaped in markdown
    assert "152\\.00" in result  # Current price with escaped decimal

    # Verify the ticker was created with correct symbol
    mock_ticker_class.assert_called_once_with("AAPL")


@patch("bot.yahoo_finance.yf.Ticker")
def test_query_tickers_multiple_symbols(mock_ticker_class):
    # Create mock for multiple tickers
    def create_mock_ticker(symbol):
        mock_ticker = Mock()
        mock_ticker.ticker = symbol
        mock_ticker.info = {
            "symbol": symbol,
            "shortName": f"{symbol} Inc.",
            "open": 100.0,
            "dayHigh": 105.0,
            "dayLow": 98.0,
            "currentPrice": 102.0,
            "previousClose": 100.0,
            "fiftyTwoWeekLow": 80.0,
            "fiftyTwoWeekHigh": 120.0,
            "ask": 102.1,
            "bid": 101.9,
            "volume": 500000,
        }
        return mock_ticker

    mock_ticker_class.side_effect = create_mock_ticker

    # Test with multiple symbols
    result = query_tickers(["AAPL", "GOOGL"])

    # Verify both symbols are in result
    assert "AAPL" in result
    assert "GOOGL" in result
    assert "102\\.00" in result  # Price should appear for both (escaped decimal)

    # Verify ticker was called for both symbols
    assert mock_ticker_class.call_count == 2


@patch("bot.yahoo_finance.yf.Ticker")
def test_query_tickers_api_error(mock_ticker_class):
    # Mock ticker that raises an exception
    mock_ticker_class.side_effect = Exception("API Error")

    # Test that function handles errors gracefully
    result = query_tickers("INVALID")

    # Should return empty string when all tickers fail
    assert result == ""
