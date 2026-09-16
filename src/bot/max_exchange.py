import logging
from decimal import Decimal

import httpx
from aiogram.utils.text_decorations import markdown_decoration
from pydantic import BaseModel
from pydantic import TypeAdapter

logger = logging.getLogger(__name__)

MAX_API_BASE_URL = "https://max-api.maicoin.com"


class MaxCurrency(BaseModel):
    currency: str
    type: str


class MaxTicker(BaseModel):
    market: str
    buy: Decimal
    sell: Decimal
    open: Decimal
    low: Decimal
    high: Decimal
    last: Decimal
    vol: Decimal
    vol_in_quote: Decimal


def _format_number(value: Decimal) -> str:
    return f"{value:,.8f}".rstrip("0").rstrip(".")


def _split_market(symbol: str, currencies: list[MaxCurrency]) -> tuple[str, str] | None:
    market = symbol.strip().lower().replace("/", "").replace("-", "").replace("_", "")
    currency_codes = {currency.currency.lower() for currency in currencies}
    base_currencies = sorted(
        (currency.currency.lower() for currency in currencies if currency.type == "crypto"),
        key=len,
        reverse=True,
    )
    for base_currency in base_currencies:
        quote_currency = market.removeprefix(base_currency)
        if quote_currency != market and quote_currency in currency_codes:
            return base_currency, quote_currency
    return None


def _format_ticker(ticker: MaxTicker, base_currency: str, quote_currency: str) -> str:
    quote_currency = quote_currency.upper()
    base_currency = base_currency.upper()
    change = (ticker.last / ticker.open - 1) * 100 if ticker.open else Decimal(0)
    change_symbol = "⏸️"
    if change > 0:
        change_symbol = "🔺"
    elif change < 0:
        change_symbol = "🔻"

    quote = markdown_decoration.quote
    return (
        f"📊 *MAX Exchange {quote(base_currency)}/{quote(quote_currency)}*\n"
        f"Open: `{quote(_format_number(ticker.open))}`\n"
        f"High: `{quote(_format_number(ticker.high))}`\n"
        f"Low: `{quote(_format_number(ticker.low))}`\n"
        f"Last: `{quote(_format_number(ticker.last))}`\n"
        f"Change: {change_symbol} `{quote(f'{change:.2f}%')}`\n"
        f"Bid: `{quote(_format_number(ticker.buy))}`\n"
        f"Ask: `{quote(_format_number(ticker.sell))}`\n"
        f"Volume: `{quote(f'{_format_number(ticker.vol)} {base_currency}')}`\n"
        f"24h Amount: `{quote(f'{_format_number(ticker.vol_in_quote)} {quote_currency}')}`"
    )


async def _query_max_tickers(client: httpx.AsyncClient, symbols: list[str]) -> list[str]:
    currencies_response = await client.get("/api/v3/currencies")
    currencies_response.raise_for_status()
    currencies = TypeAdapter(list[MaxCurrency]).validate_python(currencies_response.json())

    results = []
    for symbol in symbols:
        market_currencies = _split_market(symbol, currencies)
        if market_currencies is None:
            continue
        base_currency, quote_currency = market_currencies
        market = f"{base_currency}{quote_currency}"
        try:
            ticker_response = await client.get("/api/v3/ticker", params={"market": market})
            ticker_response.raise_for_status()
            ticker = MaxTicker.model_validate(ticker_response.json())
        except (httpx.HTTPError, ValueError) as error:
            logger.warning("Failed to query MAX Exchange for %s: %s", market, error)
            continue
        results.append(_format_ticker(ticker, base_currency, quote_currency))

    return results


async def query_max_tickers(symbols: list[str]) -> list[str]:
    async with httpx.AsyncClient(base_url=MAX_API_BASE_URL, timeout=30.0) as client:
        return await _query_max_tickers(client, symbols)
