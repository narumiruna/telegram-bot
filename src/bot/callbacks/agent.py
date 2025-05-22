from __future__ import annotations

import os
import textwrap
from pathlib import Path
from typing import cast

from agents import Agent
from agents import Runner
from agents import TResponseInputItem
from agents import trace
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
from ..tools import query_rate_history
from ..utils import async_load_url
from ..utils import load_json
from ..utils import parse_url
from .utils import get_message_text

INSTRUCTIONS = """
你是一位台灣繁體中文的資訊查詢助理，目標是根據使用者問題，查詢並提供正確、可靠且經查證的資訊，絕不捏造或猜測答案，並協助釐清需求。

# Instructions

- 所有回應必須使用台灣繁體中文。
- 嚴禁捏造事實或提供錯誤資訊，僅根據查詢結果作答。
- 回答前必須先查詢相關資訊，不能直接依靠記憶或推測。
- 需使用適當工具（如網路搜尋、資料庫等）取得資訊。
- 若查無資訊或不確定查詢方式，請主動向使用者釐清問題或請求更多細節。
- 每個思考步驟僅保留最多5字的簡要草稿，不需詳細展開。
- 所有內容以純文字格式呈現，不使用粗體、斜體、標題或清單符號。
- 每個段落開頭需加上適當表情符號和簡潔標題，標題應反映該段落主旨。

# Reasoning Steps

- 理解問題
- 規劃查詢
- 執行查詢
- 整理資訊
- 產生回應

# Output Format

- 純文字格式
- 每段開頭加表情符號與簡短標題
- 不使用任何粗體、斜體、標題或清單符號

# Notes

- 如遇資訊不足，主動詢問使用者以釐清需求。
- 嚴格遵守不捏造、不猜測原則。
- 保持語氣專業、簡潔、明確。
- 每個思考步驟僅留最精簡草稿，避免冗長。
- 回應前請先規劃並反思步驟，確保資訊正確無誤。
""".strip()


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


def remove_fake_id_messages(messages: list[TResponseInputItem]) -> list[TResponseInputItem]:
    filtered_messages = []
    for msg in messages:
        msg_type = msg.get("id")
        if msg_type == "__fake_id__":
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
            tools=[query_rate_history],
            mcp_servers=[
                MCPServerStdio(
                    params=cast(MCPServerStdioParams, params.model_dump()),
                    name=name,
                    client_session_timeout_seconds=300,
                )
                for name, params in config.items()
            ],
        )
        return cls(agent)

    def __init__(self, agent: Agent, max_cache_size: int = 50) -> None:
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

    async def handle_message(self, message: Message) -> None:
        message_text = get_message_text(message, include_reply_to_message=True, include_user_name=True)
        if not message_text:
            return

        # if the message is a reply to another message, get the previous messages
        messages = []
        if message.reply_to_message is not None:
            key = f"bot:{message.reply_to_message.id}:{message.chat.id}"
            messages = await self.cache.get(key, default=[])

        # remove all tool messages from the memory
        messages = remove_tool_messages(messages)
        messages = remove_fake_id_messages(messages)

        # replace the URL with the content
        message_text = await self.load_url_content(message_text)

        # add the user message to the list of messages
        messages.append({"role": "user", "content": message_text})

        # send the messages to the agent
        result = await Runner.run(self.agent, input=messages)
        logger.info("New items: {new_items}", new_items=result.new_items)

        # update the memory
        input_items = result.to_input_list()
        if len(input_items) > self.max_cache_size:
            input_items = input_items[-self.max_cache_size :]

        new_message = await message.reply_text(result.final_output)
        new_key = f"bot:{new_message.id}:{message.chat.id}"
        await self.cache.set(new_key, input_items)

    async def handle_command(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None:
            return

        with trace("handle_command"):
            await self.handle_message(update.message)

    async def handle_reply(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        # TODO: Implement filters.MessageFilter for reply to bot
        if (
            update.message is None
            or update.message.reply_to_message is None
            or update.message.reply_to_message.from_user is None
            or not update.message.reply_to_message.from_user.is_bot
        ):
            return

        with trace("handle_reply"):
            await self.handle_message(update.message)
