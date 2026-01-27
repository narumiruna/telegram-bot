from __future__ import annotations

import os

from aiogram import Bot
from aiogram import Dispatcher
from aiogram import F
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import ErrorEvent
from loguru import logger

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


def get_chat_filter():
    """Create a filter for allowed chats based on whitelist.

    Returns a filter function that checks if the chat_id is in the whitelist.
    """
    whitelist = os.getenv("BOT_WHITELIST")
    if not whitelist:
        logger.warning("No whitelist specified, allowing all chats")
        return lambda _: True
    else:
        chat_ids = [int(chat_id) for chat_id in whitelist.replace(" ", "").split(",")]

        def chat_filter(message) -> bool:
            return message.chat.id in chat_ids

        return chat_filter


def get_bot_token() -> str:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN is not set")
    return token


async def run_bot() -> None:  # noqa
    # Create bot and dispatcher
    bot = Bot(token=get_bot_token())
    dp = Dispatcher()

    # Create router for handlers
    router = Router()

    # Get chat filter
    chat_filter = get_chat_filter()

    # Initialize agent callback
    agent_callback = AgentCallback.from_env()

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

    # Register command handlers
    router.message.register(agent_callback.handle_command, Command("a"), F.func(chat_filter))
    router.message.register(agent_callback.handle_command, Command("gpt"), F.func(chat_filter))
    router.message.register(HelpCallback(helps=helps), Command("help"), F.func(chat_filter))
    router.message.register(summarize_callback, Command("s"), F.func(chat_filter))
    router.message.register(TranslationCallback("日本語"), Command("jp"), F.func(chat_filter))
    router.message.register(TranslationCallback("台灣正體中文"), Command("tc"), F.func(chat_filter))
    router.message.register(TranslationCallback("English"), Command("en"), F.func(chat_filter))
    router.message.register(query_ticker_callback, Command("t"), F.func(chat_filter))
    router.message.register(search_youtube_callback, Command("yt"), F.func(chat_filter))
    router.message.register(format_callback, Command("f"), F.func(chat_filter))
    router.message.register(echo_callback, Command("echo"))

    # Register reply handler (for replies to bot messages)
    router.message.register(agent_callback.handle_reply, F.reply_to_message, F.func(chat_filter))

    # Register file handler (should be last among message handlers)
    router.message.register(file_callback, F.document, F.func(chat_filter))

    # Register error handler
    error_callback = ErrorCallback(os.getenv("DEVELOPER_CHAT_ID"))

    @router.error()
    async def error_handler(event: ErrorEvent) -> None:
        await error_callback(event, bot)

    # Include router in dispatcher
    dp.include_router(router)

    # Connect to MCP servers
    await agent_callback.connect()

    try:
        # Start polling
        await dp.start_polling(bot)
    finally:
        # Cleanup on shutdown
        await agent_callback.cleanup()
        await bot.session.close()
