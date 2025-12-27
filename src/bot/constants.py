"""Bot-wide constants."""

from __future__ import annotations

from typing import Final

# Maximum message length before creating a Telegraph page
MAX_MESSAGE_LENGTH: Final[int] = 1_000

# Cache TTL in seconds (1 week)
CACHE_TTL_SECONDS: Final[int] = 604800
