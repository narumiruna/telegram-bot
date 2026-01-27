from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from agents import Agent
from agents.mcp import MCPServerManager
from agents.mcp.server import MCPServerStdio
from agents.mcp.server import MCPServerStdioParams
from loguru import logger

from bot.settings import settings
from bot.tools import execute_command
from bot.tools import query_rate_history
from bot.tools import web_search

from ..model import get_openai_model

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


def _build_mcp_servers() -> list[MCPServerStdio]:
    servers = [
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
        MCPServerStdio(
            params=MCPServerStdioParams(
                command="uvx",
                args=["gurume@latest", "mcp"],
            ),
            name="gurume",
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
                query_rate_history,
                execute_command,
                web_search,
            ],
            mcp_servers=manager.active_servers,
        )
        yield agent
