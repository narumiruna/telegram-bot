from __future__ import annotations

import json
import logging

from aiogram.enums import ParseMode
from aiogram.types import Message
from twse.stock_info import get_stock_info

from bot.callbacks.utils import safe_callback
from bot.callbacks.utils import strip_command
from bot.yahoo_finance import query_tickers

logger = logging.getLogger(__name__)


def _get_symbols(message: Message) -> list[str]:
    text = strip_command(message.text or "")
    if not text:
        return []

    return text.split()


def _query_yahoo(symbols: list[str]) -> str:
    try:
        return query_tickers(symbols)
    except Exception as e:
        logger.warning("Failed to query Yahoo Finance for %s: %s", symbols, e)
        return ""


async def _query_twse(symbols: list[str]) -> list[str]:
    results = []
    for symbol in symbols:
        try:
            result = await get_stock_info(symbol.strip())
        except json.JSONDecodeError as e:
            logger.warning("Failed to query TWSE for %s: %s", symbol, e)
            continue
        if result.msg_array:
            results.append(result.pretty_repr())
    return results


def _combine_results(yf_result: str, twse_results: list[str]) -> str:
    results = []
    if yf_result:
        results.append(yf_result)
    results.extend([result for result in twse_results if result])
    return "\n\n".join(results).strip()


@safe_callback
async def query_ticker_callback(message: Message) -> None:
    symbols = _get_symbols(message)
    if not symbols:
        return

    yf_result = _query_yahoo(symbols)
    twse_results = await _query_twse(symbols)
    result = _combine_results(yf_result, twse_results)

    if not result:
        await message.answer(f"無法查詢到股票代碼 {', '.join(symbols)} 的資訊。\n請確認代碼是否正確，或稍後再試。")
        return

    await message.answer(result, parse_mode=ParseMode.MARKDOWN_V2)
