import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from agents import Agent
from agents.mcp import MCPServerManager
from agents.mcp.server import MCPServer
from agents.mcp.server import MCPServerStdio
from agents.mcp.server import MCPServerStdioParams
from agents.mcp.server import MCPServerStreamableHttp
from agents.mcp.server import MCPServerStreamableHttpParams

from bot.provider import get_openai_model
from bot.settings import settings

# from bot.tools import execute_command
# from bot.tools import query_rate_history
# from bot.tools import web_search

logger = logging.getLogger(__name__)

current_time = datetime.now(ZoneInfo("Asia/Taipei"))

INSTRUCTIONS = f"""
You are a Telegram assistant.

# Goal
Solve the user's request correctly and clearly. Be concise by default, and add details only when needed.

# Response style
- Default language: Traditional Chinese (Taiwan).
- Be direct and compact.
- Start with the answer. Add details only when needed.
- Avoid filler, repetition, and generic disclaimers.
- Use bullets or numbered steps only when they improve clarity.
- Ask at most one clarifying question when required; otherwise make one
  reasonable assumption and state it briefly.

# Truthfulness
- Do not fabricate facts, links, quotes, tool outputs, or sources.
- Treat user-provided data as unverified unless corroborated.
- If information is unknown or unverifiable, say so clearly.
- If you make an assumption, label it as an assumption.

# Web and time-sensitive requests
- Use web search only when the request needs current or externally
  verifiable information.
- If web access is unavailable, say so and answer with what is known.
- For "latest/current/recent" questions, include the reference time below.

# Safety
- Do not help with wrongdoing, privacy invasion, malware, or evasion.
- Never request passwords, private keys, or 2FA codes.

# Output rules
- Return only the user-facing answer.
- Use section headers only when they add value.
- If code or config is requested, return exactly one code block.

Current time: {current_time}
""".strip()  # noqa


def _build_mcp_servers() -> list[MCPServer]:
    servers: list[MCPServer] = [
        # MCPServerStdio(
        #     params=MCPServerStdioParams(
        #         command="npx",
        #         args=["-y", "@playwright/mcp@latest"],
        #     ),
        #     name="playwright",
        #     client_session_timeout_seconds=settings.mcp_server_timeout,
        # ),
        MCPServerStdio(
            params=MCPServerStdioParams(
                command="uvx",
                args=["yfmcp@latest"],
            ),
            name="yfmcp",
            client_session_timeout_seconds=settings.mcp_server_timeout,
        ),
        # MCPServerStdio(
        #     params=MCPServerStdioParams(
        #         command="uvx",
        #         args=["gurume@latest", "mcp"],
        #     ),
        #     name="gurume",
        #     client_session_timeout_seconds=settings.mcp_server_timeout,
        # ),
    ]

    if settings.firecrawl_api_key:
        servers.append(
            MCPServerStdio(
                params=MCPServerStdioParams(
                    command="npx",
                    args=["-y", "firecrawl-mcp"],
                    env={"FIRECRAWL_API_KEY": settings.firecrawl_api_key},
                ),
                name="firecrawl-mcp",
                client_session_timeout_seconds=settings.mcp_server_timeout,
            )
        )
    else:
        logger.warning("FIRECRAWL_API_KEY is not set; skipping Firecrawl MCP server setup.")

    if settings.serpapi_api_key is not None:
        servers.append(
            MCPServerStreamableHttp(
                params=MCPServerStreamableHttpParams(url=f"https://mcp.serpapi.com/{settings.serpapi_api_key}/mcp"),
                name="serpapi",
                client_session_timeout_seconds=settings.mcp_server_timeout,
            )
        )
    else:
        logger.warning("SERPAPI_API_KEY is not set; skipping SerpAPI MCP server setup.")

    return servers


@asynccontextmanager
async def build_chat_agent() -> AsyncIterator[Agent]:
    mcp_servers = _build_mcp_servers()
    async with MCPServerManager(mcp_servers) as manager:
        agent = Agent(
            name="chat-agent",
            instructions=INSTRUCTIONS,
            model=get_openai_model(),
            tools=[
                # query_rate_history,
                # execute_command,
                # web_search,
            ],
            mcp_servers=manager.active_servers,
        )
        yield agent
