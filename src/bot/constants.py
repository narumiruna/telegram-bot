"""Bot-wide constants."""

from __future__ import annotations

from typing import Final

from .settings import settings

# Maximum message length before creating a Telegraph page
MAX_MESSAGE_LENGTH: Final[int] = settings.max_message_length

# Cache TTL in seconds (1 week)
CACHE_TTL_SECONDS: Final[int] = settings.cache_ttl_seconds

# MCP server connection timeout in seconds (default: 30s)
MCP_CONNECT_TIMEOUT: Final[int] = settings.mcp_connect_timeout

# MCP server cleanup timeout in seconds (default: 10s)
MCP_CLEANUP_TIMEOUT: Final[int] = settings.mcp_cleanup_timeout

# Overall shutdown timeout in seconds (default: 20s)
SHUTDOWN_TIMEOUT: Final[int] = settings.shutdown_timeout

# Timeout for MCP server responses in seconds
MCP_SERVER_TIMEOUT: Final[int] = settings.mcp_server_timeout
