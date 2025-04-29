from __future__ import annotations

import os
from pathlib import Path

from mcp.client.stdio import StdioServerParameters
from pydantic import BaseModel
from pydantic import field_validator

from .utils import load_json


class AgentConfig(BaseModel):
    name: str
    instructions: str
    mcp_servers: dict[str, StdioServerParameters]

    @classmethod
    def from_json(cls, f: str | Path) -> AgentConfig:
        data = load_json(f)
        return cls.model_validate(data)

    @field_validator("mcp_servers", mode="after")
    @classmethod
    def get_env_vars(cls, mcp_servers: dict[str, StdioServerParameters]) -> dict[str, StdioServerParameters]:
        for _, params in mcp_servers.items():
            if params.env:
                for k, v in params.env.items():
                    if v == "":
                        params.env[k] = os.getenv(k, "")
        return mcp_servers
