from __future__ import annotations

import json

from aiogram.types import Message
from loguru import logger
from twse.stock_info import get_stock_info

from ..yahoo_finance import query_tickers
from .utils import safe_callback
from .utils import strip_command


@safe_callback
async def query_ticker_callback(message: Message) -> None:
    # Extract command arguments from message text
    text = strip_command(message.text or "")
    if not text:
        return
    
    symbols = text.split()
    if not symbols:
        return

    # Query Yahoo Finance
    try:
        yf_result = query_tickers(symbols)
    except Exception as e:
        logger.warning(
            "Failed to query Yahoo Finance for {symbols}: {error}",
            symbols=symbols,
            error=str(e),
        )
        yf_result = ""

    # Query TWSE
    twse_results = []
    for symbol in symbols:
        try:
            twse_results += [get_stock_info(symbol.strip()).pretty_repr()]
        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to query TWSE for {symbol}: {error}",
                symbol=symbol,
                error=str(e),
            )
            continue

    # Combine results
    results = []
    if yf_result:
        results += [yf_result]

    for twse_result in twse_results:
        if twse_result:
            results += [twse_result]

    result = "\n\n".join(results).strip()

    if not result:
        await message.answer(
            f"無法查詢到股票代碼 {', '.join(symbols)} 的資訊。\n請確認代碼是否正確，或稍後再試。"
        )
        return

    await message.answer(result, parse_mode="MarkdownV2")
