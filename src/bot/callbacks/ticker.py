from __future__ import annotations

import json

from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.types import Update
from loguru import logger
from twse.stock_info import get_stock_info

from bot.yahoo_finance import query_tickers

from .utils import get_message_from_update
from .utils import safe_callback
from .utils import strip_command


def _get_symbols(message: Message, context: object | None) -> list[str]:
    context_args = getattr(context, "args", None)
    if context_args:
        return list(context_args)

    text = strip_command(message.text or "")
    if not text:
        return []

    return text.split()


def _query_yahoo(symbols: list[str]) -> str:
    try:
        return query_tickers(symbols)
    except Exception as e:
        logger.warning(
            "Failed to query Yahoo Finance for {symbols}: {error}",
            symbols=symbols,
            error=str(e),
        )
        return ""


async def _query_twse(symbols: list[str]) -> list[str]:
    results = []
    for symbol in symbols:
        try:
            result = await get_stock_info(symbol.strip())
        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to query TWSE for {symbol}: {error}",
                symbol=symbol,
                error=str(e),
            )
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
async def query_ticker_callback(update: Message | Update, context: object | None = None) -> None:
    message = get_message_from_update(update)
    if not message:
        return

    symbols = _get_symbols(message, context)
    if not symbols:
        return

    yf_result = _query_yahoo(symbols)
    twse_results = await _query_twse(symbols)
    result = _combine_results(yf_result, twse_results)

    if not result:
        await message.answer(f"無法查詢到股票代碼 {', '.join(symbols)} 的資訊。\n請確認代碼是否正確，或稍後再試。")
        return

    await message.answer(result, parse_mode=ParseMode.MARKDOWN_V2)
