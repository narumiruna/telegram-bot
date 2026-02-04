from __future__ import annotations

import logging
from typing import cast

from agents import Agent
from agents import Runner
from agents import TResponseInputItem
from agents import trace
from aiogram.types import Message
from aiogram.types import Update

from bot.callbacks.utils import get_message_from_update
from bot.callbacks.utils import get_processed_message_text
from bot.callbacks.utils import safe_callback
from bot.core.presentation import MessageResponse
from bot.memory import RedisSession
from bot.settings import settings

logger = logging.getLogger(__name__)


def remove_tool_messages(messages: list[TResponseInputItem]) -> list[TResponseInputItem]:
    """Remove tool-related messages from the message list.

    Args:
        messages: List of response input items

    Returns:
        Filtered list without tool messages
    """
    tool_types = {
        "function_call",
        "function_call_output",
        "computer_call",
        "computer_call_output",
        "file_search_call",
        "web_search_call",
    }
    return [msg for msg in messages if msg.get("type") not in tool_types]


def remove_fake_id_messages(messages: list[TResponseInputItem]) -> list[TResponseInputItem]:
    """Remove messages with fake IDs from the message list.

    Args:
        messages: List of response input items

    Returns:
        Filtered list without fake ID messages
    """
    return [msg for msg in messages if msg.get("id") != "__fake_id__"]


def filter_memory_messages(messages: list[TResponseInputItem]) -> list[TResponseInputItem]:
    """Apply all memory filters to a message list."""
    messages = remove_tool_messages(messages)
    return remove_fake_id_messages(messages)


class AgentCallback:
    def _make_cache_key(self, message_id: int, chat_id: int) -> str:
        """Generate a cache key for storing conversation history.

        Args:
            message_id: The Telegram message ID
            chat_id: The Telegram chat ID

        Returns:
            A cache key string
        """
        return f"bot:{message_id}:{chat_id}"

    def __init__(self, agent: Agent, max_cache_size: int = 50) -> None:
        """Initialize AgentCallback.

        Args:
            agent: The Agent instance to use
            max_cache_size: Maximum number of messages to keep in cache (default: 50)
        """
        self.agent = agent

        # max_cache_size is the maximum number of messages to keep in the cache
        self.max_cache_size = max_cache_size

    async def handle_message(self, message: Message) -> None:
        """Handle incoming message and generate response.

        Args:
            message: The Telegram message to handle
        """
        message_text, error = await get_processed_message_text(
            message,
            require_url=False,
            include_reply_to_message=True,
            include_user_name=True,
        )
        if error:
            await message.answer(error)
            return
        if not message_text:
            return

        logger.info("Handling message from chat %s", message.chat.id)

        # if the message is a reply to another message, get the previous messages
        messages = []
        if message.reply_to_message is not None:
            key = self._make_cache_key(message.reply_to_message.message_id, message.chat.id)
            logger.debug("Loading conversation history from cache: %s", key)
            session = RedisSession(
                key,
                max_cache_size=self.max_cache_size,
                ttl_seconds=settings.cache_ttl_seconds,
            )
            messages = await session.get_items()
            logger.debug("Loaded %s messages from cache", len(messages))

        # remove all tool messages from the memory
        messages = filter_memory_messages(messages)

        # add the user message to the list of messages
        messages.append(cast(TResponseInputItem, {"role": "user", "content": message_text}))

        # send the messages to the agent
        logger.info("Running agent with %s messages", len(messages))
        result = await Runner.run(self.agent, input=messages)
        logger.info("Agent completed. New items: %s", result.new_items)

        # update the memory
        input_items = filter_memory_messages(result.to_input_list())
        if len(input_items) > self.max_cache_size:
            logger.debug("Trimming conversation history to %s items", self.max_cache_size)
            input_items = input_items[-self.max_cache_size :]

        # Send response using MessageResponse for consistency and Telegraph fallback
        response = MessageResponse(
            content=result.final_output,
            title="Agent Response",
            parse_mode="HTML",  # Agent output may contain HTML formatting
        )
        new_message = await response.send(message)
        new_key = self._make_cache_key(new_message.message_id, message.chat.id)

        # Save conversation history to cache with TTL
        logger.debug(
            "Saving conversation history to cache: %s with TTL %ss",
            new_key,
            settings.cache_ttl_seconds,
        )
        new_session = RedisSession(
            new_key,
            max_cache_size=self.max_cache_size,
            ttl_seconds=settings.cache_ttl_seconds,
        )
        await new_session.set_items(input_items)
        logger.debug("Finished saving conversation history")

    @safe_callback
    async def handle_command(self, update: Message | Update, context: object | None = None) -> None:
        message = get_message_from_update(update)
        if not message:
            return

        with trace("handle_command"):
            await self.handle_message(message)

    @safe_callback
    async def handle_reply(self, update: Message | Update, context: object | None = None) -> None:
        message = get_message_from_update(update)
        if not message:
            return

        # Check if this is a reply to a bot message
        if (
            message.reply_to_message is None
            or message.reply_to_message.from_user is None
            or not message.reply_to_message.from_user.is_bot
        ):
            return

        with trace("handle_reply"):
            await self.handle_message(message)
