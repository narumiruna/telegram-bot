from collections.abc import Iterator

import httpx
import pytest

from bot.max_exchange import _query_max_tickers


def _transport(responses: Iterator[httpx.Response], requests: list[httpx.Request]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return next(responses)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_query_max_tickers_formats_supported_crypto_and_skips_other_symbols():
    requests = []
    responses = iter(
        [
            httpx.Response(
                200,
                json=[
                    {"currency": "btc", "type": "crypto"},
                    {"currency": "usdt", "type": "crypto"},
                ],
            ),
            httpx.Response(
                200,
                json={
                    "market": "btcusdt",
                    "buy": "2423808.4",
                    "sell": "2424312.5",
                    "open": "2457750.6",
                    "low": "2405746.4",
                    "high": "2472973.9",
                    "last": "2424630.9",
                    "vol": "29.8068",
                    "vol_in_quote": "71975631.110830528572",
                },
            ),
        ]
    )

    async with httpx.AsyncClient(
        base_url="https://max-api.maicoin.com",
        transport=_transport(responses, requests),
    ) as client:
        result = await _query_max_tickers(client, ["BTCUSDT", "BTC", "AAPL"])

    assert len(result) == 1
    assert result[0].startswith("📊 *MAX Exchange BTC/USDT*")
    assert "Last: `2,424,630\\.9`" in result[0]
    assert "Change: 🔻 `\\-1\\.35%`" in result[0]
    assert "Volume: `29\\.8068 BTC`" in result[0]
    assert [request.url.path for request in requests] == ["/api/v3/currencies", "/api/v3/ticker"]
    assert requests[1].url.params["market"] == "btcusdt"


@pytest.mark.asyncio
async def test_query_max_tickers_keeps_small_prices_visible():
    requests = []
    responses = iter(
        [
            httpx.Response(
                200,
                json=[
                    {"currency": "shib", "type": "crypto"},
                    {"currency": "twd", "type": "fiat"},
                ],
            ),
            httpx.Response(
                200,
                json={
                    "market": "shibtwd",
                    "buy": "0.0001551",
                    "sell": "0.0001638",
                    "open": "0.0001707",
                    "low": "0.000156",
                    "high": "0.0001711",
                    "last": "0.0001646",
                    "vol": "875285000.0",
                    "vol_in_quote": "135826.7263",
                },
            ),
        ]
    )

    async with httpx.AsyncClient(
        base_url="https://max-api.maicoin.com",
        transport=_transport(responses, requests),
    ) as client:
        result = await _query_max_tickers(client, ["shib/twd"])

    assert "Last: `0\\.0001646`" in result[0]
    assert "Volume: `875,285,000 SHIB`" in result[0]


@pytest.mark.asyncio
async def test_query_max_tickers_skips_invalid_market():
    requests = []
    responses = iter(
        [
            httpx.Response(
                200,
                json=[
                    {"currency": "coin", "type": "crypto"},
                    {"currency": "usdt", "type": "crypto"},
                ],
            ),
            httpx.Response(400, json={"success": False, "error": {"code": 1001}}),
        ]
    )

    async with httpx.AsyncClient(
        base_url="https://max-api.maicoin.com",
        transport=_transport(responses, requests),
    ) as client:
        result = await _query_max_tickers(client, ["coinusdt"])

    assert result == []
