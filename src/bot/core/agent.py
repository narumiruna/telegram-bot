import asyncio

from agents import Agent
from loguru import logger

from bot.constants import MCP_CLEANUP_TIMEOUT
from bot.constants import MCP_CONNECT_TIMEOUT


class BaseAgent(Agent):
    async def connect_mcp_servers(self) -> None:
        for mcp_server in list(self.mcp_servers):
            try:
                logger.info(
                    "Connecting to MCP server: {name} (timeout: {timeout}s)",
                    name=mcp_server.name,
                    timeout=MCP_CONNECT_TIMEOUT,
                )
                await asyncio.wait_for(mcp_server.connect(), timeout=MCP_CONNECT_TIMEOUT)
                logger.info("Successfully connected to MCP server: {name}", name=mcp_server.name)
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

    async def cleanup_mcp_servers(self) -> None:
        for mcp_server in reversed(self.mcp_servers):
            try:
                logger.info(
                    "Cleaning up MCP server: {name} (timeout: {timeout}s)",
                    name=mcp_server.name,
                    timeout=MCP_CLEANUP_TIMEOUT,
                )
                await asyncio.wait_for(mcp_server.cleanup(), timeout=MCP_CLEANUP_TIMEOUT)
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
