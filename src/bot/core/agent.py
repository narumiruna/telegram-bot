import asyncio

from agents import Agent
from loguru import logger

from bot.settings import settings


class BaseAgent(Agent):
    async def connect_mcp_servers(self) -> None:
        for mcp_server in list(self.mcp_servers):
            try:
                logger.info(
                    "Connecting to MCP server: {name} (timeout: {timeout}s)",
                    name=mcp_server.name,
                    timeout=settings.mcp_connect_timeout,
                )
                await asyncio.wait_for(mcp_server.connect(), timeout=settings.mcp_connect_timeout)
                logger.info("Successfully connected to MCP server: {name}", name=mcp_server.name)
            except asyncio.CancelledError:
                logger.info("MCP connect cancelled for server: {name}", name=mcp_server.name)
                raise
            except TimeoutError:
                logger.error(
                    "Connection timeout for MCP server {name} after {timeout}s",
                    name=mcp_server.name,
                    timeout=settings.mcp_connect_timeout,
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
                    timeout=settings.mcp_cleanup_timeout,
                )
                await asyncio.wait_for(mcp_server.cleanup(), timeout=settings.mcp_cleanup_timeout)
                logger.info("Successfully cleaned up MCP server: {name}", name=mcp_server.name)
            except asyncio.CancelledError:
                logger.info("MCP cleanup cancelled for server: {name}", name=mcp_server.name)
                raise
            except TimeoutError:
                logger.error(
                    "Cleanup timeout for MCP server {name} after {timeout}s",
                    name=mcp_server.name,
                    timeout=settings.mcp_cleanup_timeout,
                )
            except Exception as exc:
                logger.error(
                    "Failed to cleanup MCP server {name}: {error}",
                    name=mcp_server.name,
                    error=str(exc),
                )
