import asyncio
import logging
from collections.abc import Callable

from aiogram import Bot
from aiogram import Dispatcher
from aiogram import F
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.agents import build_chat_agent
from bot.callbacks import echo_callback
from bot.callbacks import error_callback
from bot.callbacks import file_callback
from bot.callbacks import generate_translation_callback
from bot.callbacks import query_ticker_callback
from bot.callbacks import search_youtube_callback
from bot.callbacks import summarize_callback
from bot.callbacks.agent import AgentCallback
from bot.callbacks.help import help_callback
from bot.callbacks.writer import writer_callback
from bot.settings import settings
from bot.shutdown import ShutdownManager

logger = logging.getLogger(__name__)


def get_chat_filter() -> Callable[[Message], bool]:
    """Create a filter for allowed chats based on whitelist.

    Returns a filter function that checks if the chat_id is in the whitelist.
    """
    chat_ids = settings.chat_ids
    if not chat_ids:
        logger.warning("No whitelist specified, allowing all chats")
        return lambda _: True

    def chat_filter(message: Message) -> bool:
        return message.chat.id in chat_ids

    return chat_filter


async def run_bot() -> None:
    async with build_chat_agent() as agent:
        # Create bot and dispatcher
        bot = Bot(token=settings.bot_token)
        dp = Dispatcher()

        # Create router for handlers
        router = Router()

        # Get chat filter
        chat_filter = get_chat_filter()

        # Initialize agent callback
        agent_callback = AgentCallback(agent, max_cache_size=settings.agent_max_cache_size)
        shutdown = ShutdownManager(settings.shutdown_timeout)
        shutdown.install_signal_handlers()

        # Register command handlers
        router.message.register(agent_callback.handle_command, Command("a"), F.func(chat_filter))
        router.message.register(agent_callback.handle_command, Command("gpt"), F.func(chat_filter))
        router.message.register(help_callback, Command("help"), F.func(chat_filter))
        router.message.register(summarize_callback, Command("s"), F.func(chat_filter))
        router.message.register(generate_translation_callback("日本語"), Command("jp"), F.func(chat_filter))
        router.message.register(generate_translation_callback("台灣正體中文"), Command("tc"), F.func(chat_filter))
        router.message.register(generate_translation_callback("English"), Command("en"), F.func(chat_filter))
        router.message.register(query_ticker_callback, Command("t"), F.func(chat_filter))
        router.message.register(search_youtube_callback, Command("yt"), F.func(chat_filter))
        router.message.register(writer_callback, Command("f"), F.func(chat_filter))
        router.message.register(writer_callback, Command("w"), F.func(chat_filter))
        router.message.register(echo_callback, Command("echo"))

        # Register reply handler (for replies to bot messages)
        router.message.register(agent_callback.handle_reply, F.reply_to_message, F.func(chat_filter))

        # Register file handler (should be last among message handlers)
        router.message.register(file_callback, F.document, F.func(chat_filter))

        # Register error handler
        router.errors.register(error_callback)

        # Include router in dispatcher
        dp.include_router(router)

        polling_task = asyncio.create_task(
            dp.start_polling(bot, handle_signals=False),
            name="bot_polling",
        )
        shutdown_task = asyncio.create_task(shutdown.wait(), name="shutdown_wait")

        try:
            done, _ = await asyncio.wait(
                {polling_task, shutdown_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            if shutdown_task in done:
                logger.info("Shutdown event triggered, stopping polling.")
                await dp.stop_polling()
                await shutdown.cancel_tasks([polling_task], reason="shutdown")
            else:
                shutdown_task.cancel()
                await shutdown.cancel_tasks([shutdown_task], reason="polling_completed")
                await polling_task
        except asyncio.CancelledError:
            logger.info("run_bot cancelled, beginning shutdown.")
            raise
        except Exception:
            logger.exception("Unexpected error in run_bot.")
            raise
        finally:
            await shutdown.cancel_tasks([polling_task, shutdown_task], reason="finalize")
            try:
                await bot.session.close()
            except Exception:
                logger.exception("Failed to close bot session.")
