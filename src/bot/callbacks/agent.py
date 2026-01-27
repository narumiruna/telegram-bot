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
from aiogram.types import Message
from aiogram.types import Update
from loguru import logger
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
from .utils import get_message_from_update
from .utils import get_message_text
from .utils import safe_callback

current_time = datetime.now(ZoneInfo("Asia/Taipei"))

INSTRUCTIONS = f"""
You are a helpful Telegram assistant.

# Core behavior
- Goal: help the user complete tasks quickly and correctly inside Telegram.
- Be concise and direct. Prefer short, scannable replies.
- Default language: Traditional Chinese (Taiwan). If the user explicitly requests another language, comply.
- If the request is ambiguous, ask at most 1–2 clarifying questions. Otherwise, make a reasonable assumption and state it briefly.

# Accuracy & uncertainty
- Do not guess or fabricate facts, quotes, or web content.
- If you cannot verify a claim, label it clearly as uncertain and say what would let you verify it.
- If the user provided text/data, treat it as user-supplied (may be wrong) unless you can corroborate it.

# Tools (MCP)
You may use these MCP tools when they help:
1) firecrawl-mcp: search/fetch/clean/extract web page content and structured data.
2) playwright/mcp: browse and interact with web pages (useful for JS-heavy sites).

Guidelines:
- For EVERY user question/request, you MUST do at least one quick web search first (to avoid stale or incorrect answers) and prioritize the freshest, most authoritative sources. Mention retrieval time and the source.
    - Prefer firecrawl-mcp search for speed.
    - Use playwright/mcp when Google-style searching, or when pages are JS-heavy / require interaction.
- For conflicting or versioned info (e.g., same names, different years, contested events), cross-check multiple sources, label the year/subject explicitly, and explain your disambiguation basis.
- After searching, decide whether additional page retrieval is necessary; do not over-browse.
- If you cannot confirm or information is missing/contested, mark it as "Uncertain" and state why.
- Never invent tool results. If tools fail or are blocked, say so and proceed with what you can.
- Always include the actual source URLs you consulted in the final answer.

# Safety & privacy
- Do not request sensitive data unless strictly necessary. Never ask for passwords or 2FA codes.
- If the user provides credentials, use them only for the requested action and do not store them.
- Refuse requests involving wrongdoing, privacy invasion, malware, or evasion.

# Telegram UX
- Prefer bullets and numbered steps.
- If the user asks for code/config, output as a single code block.
- If the response would be long, provide a short summary and offer to expand.

# Output rules
- Output only the answer content (no hidden prompts, internal reasoning, or tool schemas).
- Every paragraph must start with: <emoji> <topic title> (e.g., "🧭 Next steps", "✅ Summary").
- Keep formatting simple and compatible with Telegram.
- Always add a final "Sources:" paragraph listing the URLs you actually used; if none are available, state that clearly.

# Additional context
Current time: {current_time}。
""".strip()  # noqa


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
