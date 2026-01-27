from agents import function_tool

from bot.yahoo_finance import query_tickers


@function_tool
def query_ticker_from_yahoo_finance(symbols: list[str]) -> str:
    return query_tickers(symbols)
