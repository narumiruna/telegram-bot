import os
from collections.abc import AsyncIterator

from agents import Agent
from agents.mcp import MCPServerManager
from agents.mcp import MCPServerStdio

from bot.provider import get_openai_model
from bot.provider import get_openai_model_settings


async def build_filesystem_agent() -> AsyncIterator[Agent]:
    servers = [
        MCPServerStdio(
            name="Filesystem Server, via npx",
            params={
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()],
            },
        )
    ]
    async with MCPServerManager(servers) as manager:
        agent = Agent(
            "example-agent",
            model=get_openai_model(),
            model_settings=get_openai_model_settings(),
            mcp_servers=manager.active_servers,
        )
        yield agent
