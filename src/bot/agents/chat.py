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
你是 Telegram 助手。用繁體中文直接回答重點，必要時簡短補充。訊息若為 <name>(<username>): <message>，只處理 <message>。每個任務最多問一次關鍵缺漏，不重複確認；資訊足夠就直接執行並回結果。未知要明說，假設要標示；只要資訊不足，就必須先查詢再回答。
""".strip()  # noqa


def _build_mcp_servers() -> list[MCPServer]:
    servers: list[MCPServer] = [
        MCPServerStdio(
            params=MCPServerStdioParams(
                command="npx",
                args=["-y", "@playwright/mcp@latest"],
            ),
            name="playwright",
            client_session_timeout_seconds=settings.mcp_server_timeout,
        ),
        MCPServerStdio(
            params=MCPServerStdioParams(
                command="uvx",
                args=["yfmcp@latest"],
            ),
            name="yfmcp",
            client_session_timeout_seconds=settings.mcp_server_timeout,
        ),
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
