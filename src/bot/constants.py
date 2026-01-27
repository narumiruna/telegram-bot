"""Bot-wide constants."""

from __future__ import annotations

from typing import Final

# Maximum message length before creating a Telegraph page
MAX_MESSAGE_LENGTH: Final[int] = 1_000

# Cache TTL in seconds (1 week)
CACHE_TTL_SECONDS: Final[int] = 604800

# MCP server connection timeout in seconds (default: 30s)
MCP_CONNECT_TIMEOUT: Final[int] = 30

# MCP server cleanup timeout in seconds (default: 10s)
MCP_CLEANUP_TIMEOUT: Final[int] = 10

# Overall shutdown timeout in seconds (default: 20s)
SHUTDOWN_TIMEOUT: Final[int] = 20
