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
from bot.core.message_response import MessageResponse

logger = logging.getLogger(__name__)


class AgentCallback:
    def __init__(self, agent: Agent, max_cache_size: int = 50) -> None:
        """Initialize AgentCallback.

        Args:
            agent: The Agent instance to use
            max_cache_size: Maximum number of messages to keep in cache (default: 50)
        """
        self.agent = agent

        # max_cache_size is the maximum number of messages to keep in the cache
        self.max_cache_size = max_cache_size
        self.memory: dict[str, list[TResponseInputItem]] = {}

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

        memory_key = str(message.chat.id)
        messages = self.memory.get(memory_key, []).copy()
        logger.debug("Loaded %s messages from memory for chat key: %s", len(messages), memory_key)

        # add the user message to the list of messages
        messages.append(cast(TResponseInputItem, {"role": "user", "content": message_text}))

        # send the messages to the agent
        logger.info("Running agent with %s messages", len(messages))
        result = await Runner.run(self.agent, input=messages)
        logger.info("Agent completed. New items: %s", result.new_items)

        # update the memory
        input_items = result.to_input_list()
        if len(input_items) > self.max_cache_size:
            logger.debug("Trimming conversation history to %s items", self.max_cache_size)
            input_items = input_items[-self.max_cache_size :]

        # Send response using MessageResponse for consistency and Telegraph fallback
        response = MessageResponse(content=result.final_output)
        await response.answer(message)

        # Save conversation history in local process memory.
        self.memory[memory_key] = input_items
        logger.debug("Saved %s messages to memory for chat key: %s", len(input_items), memory_key)

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

        # Check if this is a reply to this bot's own message
        if (
            message.reply_to_message is None
            or message.reply_to_message.from_user is None
            or message.bot is None
            or message.reply_to_message.from_user.id != message.bot.id
        ):
            return

        with trace("handle_reply"):
            await self.handle_message(message)
