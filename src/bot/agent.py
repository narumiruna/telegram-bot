from __future__ import annotations

import textwrap

from agents import Agent
from agents import Runner
from agents import handoff
from agents.extensions import handoff_filters
from agents.mcp import MCPServerStdio
from loguru import logger
from telegram import Message
from telegram import Update
from telegram.ext import CommandHandler
from telegram.ext import ContextTypes
from telegram.ext import filters

from bot.utils import async_load_url

from .cache import get_cache_from_env
from .callbacks.utils import get_message_text
from .config import ServiceParams
from .model import get_openai_model
from .model import get_openai_model_settings
from .utils import parse_url


def shorten_text(text: str, width: int = 100, placeholder: str = "...") -> str:
    return textwrap.shorten(text, width=width, placeholder=placeholder)


def remove_tool_messages(messages):
    filtered_messages = []
    tool_types = [
        "function_call",
        "function_call_output",
        "computer_call",
        "computer_call_output",
        "file_search_call",
        "web_search_call",
    ]
    for msg in messages:
        msg_type = msg.get("type")
        if msg_type in tool_types:
            continue
        filtered_messages.append(msg)
    return filtered_messages


class AgentService:
    def __init__(self, params: ServiceParams, max_cache_size: int = 100) -> None:
        self.command = params["command"]
        self.help = params["help"]

        agent_params = params["agent"]

        self.handoff_agents = [
            Agent(
                name=agent["name"],
                instructions=agent["instructions"],
                model=get_openai_model(),
                model_settings=get_openai_model_settings(),
                mcp_servers=[MCPServerStdio(params=p) for p in agent["mcp_servers"].values()],
            )
            for agent in params["handoffs"]
        ]

        self.triage_agent = Agent(
            name=agent_params["name"],
            instructions=agent_params["instructions"],
            model=get_openai_model(),
            model_settings=get_openai_model_settings(),
            mcp_servers=[MCPServerStdio(params=p) for p in agent_params["mcp_servers"].values()],
            handoffs=[handoff(agent, input_filter=handoff_filters.remove_all_tools) for agent in self.handoff_agents],
        )

        # Set the current agent to the triage agent
        self._current_agent = self.triage_agent

        # max_cache_size is the maximum number of messages to keep in the cache
        self.max_cache_size = max_cache_size

        # message.chat.id -> list of messages
        self.cache = get_cache_from_env()

    async def connect(self) -> None:
        for mcp_server in self.triage_agent.mcp_servers:
            await mcp_server.connect()

        for agent in self.handoff_agents:
            for mcp_server in agent.mcp_servers:
                await mcp_server.connect()

    async def cleanup(self) -> None:
        for mcp_server in self.triage_agent.mcp_servers:
            await mcp_server.cleanup()

        for agent in self.handoff_agents:
            for mcp_server in agent.mcp_servers:
                await mcp_server.cleanup()

    def get_command_handler(self, filters: filters.BaseFilter) -> CommandHandler:
        return CommandHandler(command=self.command, callback=self.handle_command, filters=filters)

    async def load_url_content(self, message_text: str) -> str:
        parsed_url = parse_url(message_text)
        if not parsed_url:
            return message_text

        url_content = await async_load_url(parsed_url)
        message_text = message_text.replace(
            parsed_url,
            f"[URL content from {parsed_url}]:\n'''\n{url_content}\n'''\n[END of URL content]\n",
            1,
        )
        return message_text

    async def handle_message(
        self,
        message: Message,
        include_reply_to_message: bool = False,
        use_triage_agent: bool = False,
    ) -> None:
        message_text = get_message_text(
            message,
            include_reply_to_message=include_reply_to_message,
            include_user_name=True,
        )
        if not message_text:
            return

        # Get the memory for the current chat (group or user)
        key = f"bot:{message.chat.id}"
        messages = await self.cache.get(key)
        if messages is None:
            messages = []
            logger.info("No key found for {key}", key=key)

        # remove all tool messages from the memory
        messages = remove_tool_messages(messages)

        # replace the URL with the content
        message_text = await self.load_url_content(message_text)

        # add the user message to the list of messages
        messages.append(
            {
                "role": "user",
                "content": message_text,
            }
        )

        # send the messages to the agent
        if use_triage_agent:
            self._current_agent = self.triage_agent
        result = await Runner.run(self._current_agent, input=messages)

        logger.info("New items: {new_items}", new_items=result.new_items)

        # update the memory
        input_items = result.to_input_list()
        messages = remove_tool_messages(messages)
        if len(input_items) > self.max_cache_size:
            input_items = input_items[-self.max_cache_size :]
        await self.cache.set(key, input_items)

        # handoff to another agent
        self._current_agent = result.last_agent

        await message.reply_text(result.final_output)

    async def handle_command(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        if not message:
            return

        await self.handle_message(message, include_reply_to_message=True, use_triage_agent=True)

    async def handle_reply(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        # TODO: Implement filters.MessageFilter for reply to bot

        message = update.message
        if not message:
            return

        reply_to_message = message.reply_to_message
        if not reply_to_message:
            return

        from_user = reply_to_message.from_user
        if not from_user:
            return

        if not from_user.is_bot:
            return

        await self.handle_message(message, include_reply_to_message=True, use_triage_agent=False)
