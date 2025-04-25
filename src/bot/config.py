from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

from agents.mcp import MCPServerStdioParams


class ServiceParams(TypedDict):
    command: str
    help: str
    agent: AgentParams


class AgentParams(TypedDict):
    name: str
    instructions: str
    tools: list[str]
    mcp_servers: dict[str, MCPServerStdioParams]
    output_type: str | None


def load_config(f: str | Path) -> ServiceParams:
    path = Path(f)
    if path.suffix != ".json":
        raise ValueError(f"File {f} is not a json file")

    with open(path) as fp:
        return json.load(fp)
