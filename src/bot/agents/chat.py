from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import cast
from zoneinfo import ZoneInfo

from agents import Agent
from agents.mcp import MCPServer
from agents.mcp.server import MCPServerStdio
from agents.mcp.server import MCPServerStdioParams
from loguru import logger

from bot.tools import execute_command
from bot.tools import query_rate_history
from bot.tools import web_search

from ..constants import MCP_CLEANUP_TIMEOUT
from ..constants import MCP_CONNECT_TIMEOUT
from ..model import get_openai_model
from ..model import get_openai_model_settings

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

Guidelines:
- For EVERY user question/request, you MUST do at least one quick web search first (to avoid stale or incorrect answers) and prioritize the freshest, most authoritative sources. Mention retrieval time and the source.
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


def _build_mcp_servers(mcp_timeout: int, firecrawl_api_key: str) -> list[MCPServerStdio]:
    return [
        MCPServerStdio(
            params=MCPServerStdioParams(
                command="npx",
                args=["-y", "@playwright/mcp@latest"],
            ),
            name="playwright",
            client_session_timeout_seconds=mcp_timeout,
        ),
        MCPServerStdio(
            params=MCPServerStdioParams(
                command="npx",
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


async def _connect_mcp_servers(mcp_servers: list[MCPServerStdio]) -> list[MCPServerStdio]:
    connected_servers: list[MCPServerStdio] = []
    for mcp_server in list(mcp_servers):
        try:
            logger.info(
                "Connecting to MCP server: {name} (timeout: {timeout}s)",
                name=mcp_server.name,
                timeout=MCP_CONNECT_TIMEOUT,
            )
            await asyncio.wait_for(mcp_server.__aenter__(), timeout=MCP_CONNECT_TIMEOUT)
            logger.info("Successfully connected to MCP server: {name}", name=mcp_server.name)
            connected_servers.append(mcp_server)
        except asyncio.CancelledError:
            logger.info("MCP connect cancelled for server: {name}", name=mcp_server.name)
            raise
        except TimeoutError:
            logger.error(
                "Connection timeout for MCP server {name} after {timeout}s",
                name=mcp_server.name,
                timeout=MCP_CONNECT_TIMEOUT,
            )
        except Exception as exc:
            logger.error(
                "Failed to connect to MCP server {name}: {error}",
                name=mcp_server.name,
                error=str(exc),
            )
    return connected_servers


async def _cleanup_mcp_servers(connected_servers: list[MCPServerStdio]) -> None:
    for mcp_server in reversed(connected_servers):
        try:
            logger.info(
                "Cleaning up MCP server: {name} (timeout: {timeout}s)",
                name=mcp_server.name,
                timeout=MCP_CLEANUP_TIMEOUT,
            )
            await asyncio.wait_for(mcp_server.__aexit__(None, None, None), timeout=MCP_CLEANUP_TIMEOUT)
            logger.info("Successfully cleaned up MCP server: {name}", name=mcp_server.name)
        except asyncio.CancelledError:
            logger.info("MCP cleanup cancelled for server: {name}", name=mcp_server.name)
            raise
        except TimeoutError:
            logger.error(
                "Cleanup timeout for MCP server {name} after {timeout}s",
                name=mcp_server.name,
                timeout=MCP_CLEANUP_TIMEOUT,
            )
        except Exception as exc:
            logger.error(
                "Failed to cleanup MCP server {name}: {error}",
                name=mcp_server.name,
                error=str(exc),
            )


@asynccontextmanager
async def build_chat_agent() -> AsyncIterator[Agent]:
    mcp_timeout = int(os.getenv("MCP_SERVER_TIMEOUT", "300"))

    firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
    if not firecrawl_api_key:
        raise ValueError("FIRECRAWL_API_KEY environment variable is not set")

    mcp_servers = _build_mcp_servers(mcp_timeout=mcp_timeout, firecrawl_api_key=firecrawl_api_key)
    connected_servers: list[MCPServerStdio] = []
    try:
        connected_servers = await _connect_mcp_servers(mcp_servers)
        if len(connected_servers) != len(mcp_servers):
            removed_count = len(mcp_servers) - len(connected_servers)
            logger.warning("Disabling {count} MCP servers that failed to connect", count=removed_count)

        agent = Agent(
            name="agent",
            instructions=INSTRUCTIONS,
            model=get_openai_model(),
            model_settings=get_openai_model_settings(),
            tools=[
                query_rate_history,
                execute_command,
                web_search,
            ],
            mcp_servers=cast(list[MCPServer], connected_servers),
        )

        yield agent
    finally:
        await _cleanup_mcp_servers(connected_servers)
