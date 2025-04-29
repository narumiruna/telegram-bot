from __future__ import annotations

from typing import TypedDict

from agents.mcp import MCPServerStdioParams


class AgentConfig(TypedDict):
    name: str
    instructions: str
    tools: list[str]
    mcp_servers: dict[str, MCPServerStdioParams]
    output_type: str | None
