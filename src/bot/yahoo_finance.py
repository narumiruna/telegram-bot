import logging
import re
from typing import Any

import yfinance as yf

logger = logging.getLogger(__name__)


class TickerError(Exception):
    """Exception raised for errors in ticker retrieval or processing."""

    def __init__(self, symbol: str, reason: str = "") -> None:
        message = f"Failed to get ticker for {symbol}"
        if reason:
            message += f": {reason}"
        super().__init__(message)


def to_float(value: Any) -> float:
    """Convert a value to float if possible.

    Args:
        value: Value to convert to float

    Returns:
        Float value if conversion is successful, 0.0 otherwise
    """
    if value is None:
        return 0.0

    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def to_str(value: Any) -> str:
    """Convert a value to string.

    Args:
        value: Value to convert to string

    Returns:
        String representation of the value, or "N/A" if None
    """
    return str(value) if value is not None else "N/A"


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2 format.

    Args:
        text: Text to escape, can be None or any type

    Returns:
        Escaped text string, or empty string if input is None
    """
    # Convert to string first
    pattern = r"([_*\[\]()~`>#+=|{}.!-])"
    return re.sub(pattern, r"\\\1", text)


def format_value(value: float) -> str:
    return escape_markdown(f"{value:.2f}")


def query_tickers(symbols: str | list[str]) -> str:
    """Query multiple ticker symbols and return formatted information.

    Args:
        symbols: Single ticker symbol or list of symbols

    Returns:
        Formatted string with ticker information
    """
    if isinstance(symbols, str):
        symbols = [s.strip() for s in symbols.split(",") if s.strip()]

    symbols = [s.upper().strip() for s in symbols]

    results = []
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            results.append(format_ticker_info(ticker))
        except Exception as e:
            logger.info("Failed to get ticker for %s, got error: %s", symbol, e)

    return "\n\n".join(results).strip()


def get_info(ticker: yf.Ticker) -> dict[str, Any]:
    """Get ticker information safely.

    Args:
        ticker: yfinance Ticker object

    Returns:
        Dictionary with ticker information

    Raises:
        TickerError: If ticker information cannot be retrieved
    """
    try:
        info = ticker.info
        # Check if we got valid data
        if not info or not isinstance(info, dict):
            raise TickerError(ticker.ticker, "Received empty or invalid data") from None
    except Exception as e:
        raise TickerError(ticker.ticker, str(e)) from e

    return info


def format_ticker_info(ticker: yf.Ticker) -> str:
    """Generate a formatted representation of ticker information.

    Args:
        ticker: yfinance Ticker object

    Returns:
        Formatted string with ticker information
    """
    info = get_info(ticker)

    # Extract basic information
    symbol = to_str(info.get("symbol", "Unknown"))
    short_name = to_str(info.get("shortName", symbol))

    # Extract price information
    open_price = to_float(info.get("open"))
    high_price = to_float(info.get("dayHigh"))
    low_price = to_float(info.get("dayLow"))
    last_price = to_float(info.get("currentPrice"))
    previous_close = to_float(info.get("previousClose"))
    fifty_two_week_low = to_float(info.get("fiftyTwoWeekLow"))
    fifty_two_week_high = to_float(info.get("fiftyTwoWeekHigh"))
    ask_price = to_float(info.get("ask"))
    bid_price = to_float(info.get("bid"))
    volume = to_float(info.get("volume"))

    # Check for essential data
    if all(p == 0.0 for p in [open_price, high_price, low_price]):
        raise TickerError(symbol, "Missing essential price data")

    # Calculate derived values: always return float
    mid_price = (ask_price + bid_price) / 2  # ask_price and bid_price are floats
    effective_last_price = last_price if last_price > 0.0 else mid_price

    # Calculate price change
    net_change = 0.0
    if effective_last_price > 0.0 and previous_close > 0.0:
        net_change = (effective_last_price / previous_close - 1.0) * 100

    # Determine change indicator
    net_change_symbol = "⏸️"
    if net_change > 0:
        net_change_symbol = "🔺"
    elif net_change < 0:
        net_change_symbol = "🔻"

    # Build the formatted output
    return (
        f"📊 *{escape_markdown(short_name)} \\({escape_markdown(symbol)}\\)*\n"
        f"Open: `{format_value(open_price)}`\n"
        f"High: `{format_value(high_price)}`\n"
        f"Low: `{format_value(low_price)}`\n"
        f"Last: `{format_value(effective_last_price)}`\n"
        f"Change: {net_change_symbol} `{escape_markdown(f'{net_change:.2f}%')}`\n"
        f"Volume: `{format_value(volume)}`\n"
        f"52 Week Low: `{format_value(fifty_two_week_low)}`\n"
        f"52 Week High: `{format_value(fifty_two_week_high)}`"
    )
