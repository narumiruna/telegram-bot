from __future__ import annotations

import os
import textwrap
from pathlib import Path
from textwrap import dedent
from typing import cast

from agents import Agent
from agents import Runner
from agents import TResponseInputItem
from agents.mcp import MCPServerStdio
from agents.mcp import MCPServerStdioParams
from loguru import logger
from mcp.client.stdio import StdioServerParameters
from telegram import Message
from telegram import Update
from telegram.ext import ContextTypes

from ..cache import get_cache_from_env
from ..model import get_openai_model
from ..model import get_openai_model_settings
from ..utils import async_load_url
from ..utils import load_json
from ..utils import parse_url
from .utils import get_message_text

INSTRUCTIONS = dedent(
    """
- 使用台灣繁體中文
- 不捏造任何事實，不提供錯誤資訊
- 會使用適當的工具來取得所需的資訊
- 回答問題前一定會先查詢資訊
- 若查不到所需的資訊，或不知道怎麼查詢，先向使用者釐清問題
- Think step by step, but only keep a minimum draft for each thinking step, with 5 words at most.
- 將所有內容以純文字格式呈現，不使用粗體、斜體、標題或清單符號。每個段落應該以適當的表情符號和簡潔的標題開始
""".strip()
)


def load_mcp_config(f: str | Path) -> dict[str, StdioServerParameters]:
    data = load_json(f)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid configuration file: {f}")

    result = {}
    for name, params in data.items():
        if not isinstance(params, dict):
            raise ValueError(f"Invalid parameters for {name}: {params}")

        env_vars = params.get("env")
        if isinstance(env_vars, dict):
            for k, v in env_vars.items():
                if v == "":
                    env_vars[k] = os.getenv(k, "")

        result[name] = StdioServerParameters.model_validate(params)
    return result


def shorten_text(text: str, width: int = 100, placeholder: str = "...") -> str:
    return textwrap.shorten(text, width=width, placeholder=placeholder)


def remove_tool_messages(messages: list[TResponseInputItem]) -> list[TResponseInputItem]:
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


class AgentCallback:
    @classmethod
    def from_config(cls, config_file: str | Path) -> AgentCallback:
        config = load_mcp_config(config_file)
        agent = Agent(
            name="agent",
            instructions=INSTRUCTIONS,
            model=get_openai_model(),
            model_settings=get_openai_model_settings(),
            mcp_servers=[
                MCPServerStdio(params=cast(MCPServerStdioParams, params.model_dump()), name=name)
                for name, params in config.items()
            ],
        )
        return cls(agent)

    def __init__(self, agent: Agent, max_cache_size: int = 100) -> None:
        self.agent = agent

        # max_cache_size is the maximum number of messages to keep in the cache
        self.max_cache_size = max_cache_size

        # message.chat.id -> list of messages
        self.cache = get_cache_from_env()

    async def connect(self) -> None:
        for mcp_server in self.agent.mcp_servers:
            await mcp_server.connect()

    async def cleanup(self) -> None:
        for mcp_server in self.agent.mcp_servers:
            await mcp_server.cleanup()

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
        # for multiple agents
        # messages = remove_tool_messages(messages)

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
        result = await Runner.run(self.agent, input=messages)

        logger.info("New items: {new_items}", new_items=result.new_items)

        # update the memory
        input_items = result.to_input_list()
        if len(input_items) > self.max_cache_size:
            input_items = input_items[-self.max_cache_size :]
        await self.cache.set(key, input_items)

        await message.reply_text(result.final_output)

    async def handle_command(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        if not message:
            return

        await self.handle_message(message, include_reply_to_message=True)

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

        await self.handle_message(message, include_reply_to_message=True)
