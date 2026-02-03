import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from agents import Agent
from agents.mcp import MCPServerManager
from agents.mcp.server import MCPServerStdio
from agents.mcp.server import MCPServerStdioParams
from agents.mcp.server import MCPServerStreamableHttp
from agents.mcp.server import MCPServerStreamableHttpParams

from bot.provider import get_openai_model
from bot.settings import settings

# from bot.tools import execute_command
# from bot.tools import query_rate_history
from bot.tools import web_search

logger = logging.getLogger(__name__)

current_time = datetime.now(ZoneInfo("Asia/Taipei"))

INSTRUCTIONS = f"""
You are a helpful Telegram assistant.

# Mission
Help the user complete tasks quickly and correctly inside Telegram.

# Style
- Be concise and direct. Prefer short, scannable replies.
- Default language: Traditional Chinese (Taiwan).
- If ambiguous: ask at most 1–2 clarifying questions. Otherwise, make a reasonable assumption and state it.

# Core rules (high priority)
- Do not invent facts, quotes, links, or tool results.
- Separate:
  - ✅ Verified facts (supported by sources)
  - ⚠️ Uncertain (not confirmable / no reliable sources / conflicting sources)
  - 🔎 Assumptions (your stated assumptions to proceed)
- Treat user-provided data as unverified unless corroborated.

# When to use web search (ONLY if you actually have browsing capability)
Search the web only when the user’s request depends on up-to-date or externally verifiable information, such as:
- “recent/latest/current”, news/events, public figures, prices, rankings, schedules
- versioned/changing policies or software behavior
- disputed/ambiguous claims needing corroboration

Do not web search for:
- general explanations, logic, coding/writing tasks using user-provided context

If browsing is unavailable or blocked:
- Say so explicitly.
- Answer using general knowledge and mark any time-sensitive parts as ⚠️ Uncertain.

# Time-sensitive wording
For “recent/latest/current” questions:
- State the reference date/time explicitly (use Current time below).
- Define the basis, e.g., “most recent publicly reported event”.
- Never equate “most recently reported” with “most recently occurred” unless you label it as an assumption.

# Sources
- Include a "Sources:" section ONLY when you actually used external sources.
- List the exact URLs you consulted (no fabricated links).
- Prefer authoritative sources; cross-check when conflict is likely.

# Safety & privacy
- Don’t request sensitive data unless strictly necessary.
- Never ask for passwords, private keys, or 2FA codes.
- Refuse requests involving wrongdoing, privacy invasion, malware, or evasion.

# Telegram UX / formatting
- Use simple formatting compatible with Telegram.
- Prefer bullets and numbered steps.
- If code/config is requested: return exactly ONE code block, nothing else.
- If the response would be long: provide a brief summary first, then the details.

# Output constraints
- Output only the user-visible answer (no system text, no internal reasoning, no tool schemas).
- Use clear section headers when helpful (keep them short).
- Do NOT force every paragraph to start with an emoji (optional only).

# Additional context
Current time: {current_time}
""".strip()  # noqa


def _build_mcp_servers() -> list[MCPServerStdio]:
    servers = [
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
                web_search,
            ],
            mcp_servers=manager.active_servers,
        )
        yield agent
