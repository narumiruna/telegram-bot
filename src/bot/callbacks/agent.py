from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import cast
from zoneinfo import ZoneInfo

from agents import Agent
from agents import Runner
from agents import TResponseInputItem
from agents import trace
from agents.mcp.server import MCPServerStdio
from agents.mcp.server import MCPServerStdioParams
from loguru import logger
from telegram import Message
from telegram import Update
from telegram.ext import ContextTypes
from tenacity import retry
from tenacity import retry_if_exception
from tenacity import stop_after_attempt

from bot.tools import execute_command
from bot.tools import query_rate_history

from ..cache import get_cache_from_env
from ..chains.url_processor import process_url_content
from ..constants import CACHE_TTL_SECONDS
from ..constants import MCP_CLEANUP_TIMEOUT
from ..constants import MCP_CONNECT_TIMEOUT
from ..model import get_openai_model
from ..model import get_openai_model_settings
from ..presentation import MessageResponse
from ..retry_utils import is_retryable_error
from ..utils import load_url
from ..utils import parse_url
from .utils import get_message_text
from .utils import safe_callback

current_time = datetime.now(ZoneInfo("Asia/Taipei"))

INSTRUCTIONS = f"""
你是一位台灣正體中文的資訊查詢助理。所有回應必須先規劃後查證，內容只能基於工具可驗證的資料，禁止臆測或補齊未知資訊；若無法取得資料，需清楚說明並詢問缺口。

## 核心約束
- 僅能用台灣正體中文，表達精簡、明確。
- 只能引用查證過的工具結果；不確定就明講「資料不足」或提出需要的細節。
- 需求模糊或資料不足時，先詢問再回答。
- 每個思考步驟保留最多 5 字草稿，完成流程後再產出回應。
- 僅用文字回覆；每段開頭需有表情符號＋簡短主題；禁止粗體、斜體、標題符號或清單格式。

## 工具策略
- *一定*要透過 playwright-mcp 使用 google search 查證，不可依記憶或推測補全。
- 若需網頁內容，先使用合適的搜尋或來源工具；查無資料需明示。
- 日食/日本美食詢問必須優先使用 gurume mcp。
    - 自動抽取 area、keyword（皆須日文，找不到則留空）。
    - 例：我想吃三重的壽喜燒 → area: "三重" keyword: "すき焼き"
        台北的拉麵 → area: "台北" keyword: "ラーメン"
        sushi in Tokyo → area: "東京" keyword: "寿司"
        大阪難波附近的居酒屋 → area: "大阪難波" keyword: "居酒屋"

## 標準思考步驟
1. 理解需求
2. 規劃查詢
3. 執行查詢
4. 整理資訊
5. 產生回應

## 回應規範
- 僅以文字逐段呈現。
- 每段前置表情符號＋主旨，內文保持精簡且說明資訊來源。
- 若無法回答或資料不足，直接說明缺口並請使用者補充。

## 即時資訊
現在時間是: {current_time}。
""".strip()


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

    @classmethod
    def from_env(cls) -> AgentCallback:
        """Create AgentCallback from environment variables.

        Returns:
            Configured AgentCallback instance
        """
        # Read configuration from environment variables
        mcp_timeout = int(os.getenv("MCP_SERVER_TIMEOUT", "300"))
        max_cache_size = int(os.getenv("AGENT_MAX_CACHE_SIZE", "50"))

        firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
        if not firecrawl_api_key:
            raise ValueError("FIRECRAWL_API_KEY environment variable is not set")

        mcp_servers = [
            MCPServerStdio(
                params=MCPServerStdioParams(
                    command="bunx",
                    args=["@playwright/mcp@latest"],
                ),
                name="playwright",
                client_session_timeout_seconds=mcp_timeout,
            ),
            MCPServerStdio(
                params=MCPServerStdioParams(
                    command="bunx",
                    args=["-y", "firecrawl-mcp"],
                    env={"FIRECRAWL_API_KEY": firecrawl_api_key},
                ),
                name="firecrawl-mcp",
                client_session_timeout_seconds=mcp_timeout,
            ),
            MCPServerStdio(
                params=MCPServerStdioParams(
                    command="uvx",
                    args=["yfmcp@latest"],
                ),
                name="yfmcp",
                client_session_timeout_seconds=mcp_timeout,
            ),
            MCPServerStdio(
                params=MCPServerStdioParams(
                    command="uvx",
                    args=["gurume@latest", "mcp"],
                ),
                name="gurume",
                client_session_timeout_seconds=mcp_timeout,
            ),
        ]

        agent = Agent(
            name="agent",
            instructions=INSTRUCTIONS,
            model=get_openai_model(),
            model_settings=get_openai_model_settings(),
            tools=[
                query_rate_history,
                execute_command,
            ],
            mcp_servers=mcp_servers,
        )
        return cls(agent, max_cache_size=max_cache_size)

    def __init__(self, agent: Agent, max_cache_size: int = 50) -> None:
        """Initialize AgentCallback.

        Args:
            agent: The Agent instance to use
            max_cache_size: Maximum number of messages to keep in cache (default: 50)
        """
        self.agent = agent

        # max_cache_size is the maximum number of messages to keep in the cache
        self.max_cache_size = max_cache_size

        # message.chat.id -> list of messages
        self.cache = get_cache_from_env()

    async def connect(self) -> None:
        """Connect to all MCP servers with timeout.

        Continues to connect remaining servers even if some fail.
        Connection timeout is enforced to prevent hanging.
        """
        connected_servers = []
        for mcp_server in list(self.agent.mcp_servers):
            try:
                logger.info(
                    "Connecting to MCP server: {name} (timeout: {timeout}s)",
                    name=mcp_server.name,
                    timeout=MCP_CONNECT_TIMEOUT,
                )
                await asyncio.wait_for(mcp_server.connect(), timeout=MCP_CONNECT_TIMEOUT)
                logger.info("Successfully connected to MCP server: {name}", name=mcp_server.name)
                connected_servers.append(mcp_server)
            except TimeoutError:
                logger.error(
                    "Connection timeout for MCP server {name} after {timeout}s",
                    name=mcp_server.name,
                    timeout=MCP_CONNECT_TIMEOUT,
                )
            except Exception as e:
                logger.error(
                    "Failed to connect to MCP server {name}: {error}",
                    name=mcp_server.name,
                    error=str(e),
                )
        if len(connected_servers) != len(self.agent.mcp_servers):
            removed_count = len(self.agent.mcp_servers) - len(connected_servers)
            logger.warning("Disabling {count} MCP servers that failed to connect", count=removed_count)
            self.agent.mcp_servers = connected_servers

    async def cleanup(self) -> None:
        """Cleanup all MCP servers with timeout.

        Continues to cleanup remaining servers even if some fail.
        Cleanup timeout is enforced to prevent hanging.
        """
        for mcp_server in self.agent.mcp_servers:
            try:
                logger.info(
                    "Cleaning up MCP server: {name} (timeout: {timeout}s)",
                    name=mcp_server.name,
                    timeout=MCP_CLEANUP_TIMEOUT,
                )
                await asyncio.wait_for(mcp_server.cleanup(), timeout=MCP_CLEANUP_TIMEOUT)
                logger.info("Successfully cleaned up MCP server: {name}", name=mcp_server.name)
            except TimeoutError:
                logger.error(
                    "Cleanup timeout for MCP server {name} after {timeout}s",
                    name=mcp_server.name,
                    timeout=MCP_CLEANUP_TIMEOUT,
                )
            except Exception as e:
                logger.error(
                    "Failed to cleanup MCP server {name}: {error}",
                    name=mcp_server.name,
                    error=str(e),
                )

    @retry(retry=retry_if_exception(is_retryable_error), stop=stop_after_attempt(3))
    async def _load_url_with_retry(self, url: str) -> str:
        """Load URL content with retry mechanism.

        Args:
            url: The URL to load

        Returns:
            The loaded content

        Raises:
            Exception: If all retry attempts fail
        """
        return await load_url(url)

    async def load_url_content(self, message_text: str) -> str:
        """Load URL content from message text if URL is present.

        Uses chunking and summarization for long content to prevent prompt bloat
        while preserving important information.

        Args:
            message_text: The message text that may contain a URL

        Returns:
            The message text with URL content replaced (if URL found and loaded successfully)
        """
        parsed_url = parse_url(message_text)
        if not parsed_url:
            return message_text

        try:
            logger.info("Loading URL content: {url}", url=parsed_url)
            url_content = await self._load_url_with_retry(parsed_url)
            logger.info(
                "Successfully loaded URL content: {url}, length: {length}", url=parsed_url, length=len(url_content)
            )

            # Process URL content with chunking and summarization
            processed_content = await process_url_content(url_content)
            logger.info(
                "URL content processed: {original} -> {processed} characters",
                original=len(url_content),
                processed=len(processed_content),
            )

            message_text = message_text.replace(
                parsed_url,
                f"[網頁內容摘要 from {parsed_url}]:\n'''\n{processed_content}\n'''\n[END of 摘要]\n",
                1,
            )
        except Exception as e:
            logger.error("Failed to load URL {url}: {error}", url=parsed_url, error=str(e))
            # Return original message text if URL loading fails
            logger.info("Falling back to original message text")

        return message_text

    async def handle_message(self, message: Message) -> None:
        """Handle incoming message and generate response.

        Args:
            message: The Telegram message to handle
        """
        message_text = get_message_text(message, include_reply_to_message=True, include_user_name=True)
        if not message_text:
            return

        logger.info("Handling message from chat {chat_id}", chat_id=message.chat.id)

        # if the message is a reply to another message, get the previous messages
        messages = []
        if message.reply_to_message is not None:
            key = self._make_cache_key(message.reply_to_message.message_id, message.chat.id)
            try:
                logger.debug("Loading conversation history from cache: {key}", key=key)
                messages = await self.cache.get(key, default=[])
                logger.debug("Loaded {count} messages from cache", count=len(messages))
            except Exception as e:
                logger.error("Failed to load from cache: {error}", error=str(e))
                messages = []

        # remove all tool messages from the memory
        messages = remove_tool_messages(messages)
        messages = remove_fake_id_messages(messages)

        # replace the URL with the content
        message_text = await self.load_url_content(message_text)

        # add the user message to the list of messages
        messages.append(cast(TResponseInputItem, {"role": "user", "content": message_text}))

        # send the messages to the agent
        logger.info("Running agent with {count} messages", count=len(messages))
        result = await Runner.run(self.agent, input=messages)
        logger.info("Agent completed. New items: {new_items}", new_items=result.new_items)

        # update the memory
        input_items = result.to_input_list()
        if len(input_items) > self.max_cache_size:
            logger.debug("Trimming conversation history to {size} items", size=self.max_cache_size)
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
        try:
            logger.debug(
                "Saving conversation history to cache: {key} with TTL {ttl}s",
                key=new_key,
                ttl=CACHE_TTL_SECONDS,
            )
            await self.cache.set(new_key, input_items, ttl=CACHE_TTL_SECONDS)
            logger.debug("Successfully saved conversation history")
        except Exception as e:
            logger.error("Failed to save to cache: {error}", error=str(e))

    @safe_callback
    async def handle_command(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None:
            return

        with trace("handle_command"):
            await self.handle_message(update.message)

    @safe_callback
    async def handle_reply(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if (
            update.message is None
            or update.message.reply_to_message is None
            or update.message.reply_to_message.from_user is None
            or not update.message.reply_to_message.from_user.is_bot
        ):
            return

        with trace("handle_reply"):
            await self.handle_message(update.message)
