from __future__ import annotations

import os
from typing import Annotated

import typer
from loguru import logger
from telegram import Update
from telegram.ext import Application
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import filters

from .callbacks import ErrorCallback
from .callbacks import HelpCallback
from .callbacks import TranslationCallback
from .callbacks import echo_callback
from .callbacks import file_callback
from .callbacks import format_callback
from .callbacks import query_ticker_callback
from .callbacks import search_youtube_callback
from .callbacks import summarize_callback
from .callbacks.agent import AgentCallback


def get_chat_filter() -> filters.BaseFilter:
    whitelist = os.getenv("BOT_WHITELIST")
    if not whitelist:
        logger.warning("No whitelist specified, allowing all chats")
        return filters.ALL
    else:
        chat_ids = [int(chat_id) for chat_id in whitelist.replace(" ", "").split(",")]
        return filters.Chat(chat_ids)


def get_bot_token() -> str:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN is not set")
    return token


def run_bot(config_file: Annotated[str, typer.Option("-c", "--config")] = "config/default.json") -> None:  # noqa
    chat_filter = get_chat_filter()

    agent_callback = AgentCallback.from_config(config_file)

    async def connect(application: Application) -> None:
        await agent_callback.connect()

    async def cleanup(application: Application) -> None:
        await agent_callback.cleanup()

    app = Application.builder().token(get_bot_token()).post_init(connect).post_shutdown(cleanup).build()

    helps = [
        "code: https://github.com/narumiruna/bot",
        "/help - Show this help message",
        "/a - An agent that can assist with various tasks",
        "/s - Summarize a document or URL content",
        "/jp - Translate text to Japanese",
        "/tc - Translate text to Traditional Chinese",
        "/en - Translate text to English",
        "/echo - Echo the message",
        "/yt - Search YouTube",
        "/t - Query ticker from Yahoo Finance and Taiwan stock exchange",
        "/f - Format and normalize the document in 台灣話",
    ]

    app.add_handlers(
        [
            # agent
            CommandHandler("a", agent_callback.handle_command, filters=chat_filter, block=False),
            CommandHandler("gpt", agent_callback.handle_command, filters=chat_filter, block=False),
            # help
            CommandHandler("help", HelpCallback(helps=helps), filters=chat_filter, block=False),
            CommandHandler("s", summarize_callback, filters=chat_filter, block=False),
            CommandHandler("jp", TranslationCallback("日本語"), filters=chat_filter, block=False),
            CommandHandler("tc", TranslationCallback("台灣正體中文"), filters=chat_filter, block=False),
            CommandHandler("en", TranslationCallback("English"), filters=chat_filter, block=False),
            CommandHandler("t", query_ticker_callback, filters=chat_filter, block=False),
            CommandHandler("yt", search_youtube_callback, filters=chat_filter, block=False),
            CommandHandler("f", format_callback, filters=chat_filter, block=False),
            CommandHandler("echo", echo_callback, block=False),
        ]
    )

    # Message handlers should be placed at the end.
    app.add_handler(
        MessageHandler(filters=chat_filter & filters.REPLY, callback=agent_callback.handle_reply, block=False)
    )
    app.add_handler(MessageHandler(filters=chat_filter, callback=file_callback, block=False))

    app.add_error_handler(ErrorCallback(os.getenv("DEVELOPER_CHAT_ID")), block=False)

    app.run_polling(allowed_updates=Update.ALL_TYPES)
