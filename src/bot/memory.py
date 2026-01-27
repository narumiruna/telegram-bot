from __future__ import annotations

from collections.abc import Iterable

from agents import TResponseInputItem
from agents.memory.session import SessionABC
from aiocache import BaseCache
from loguru import logger


class RedisSession(SessionABC):
    """Redis-backed session storage for conversation items."""

    def __init__(
        self,
        session_id: str,
        *,
        cache: BaseCache,
        max_cache_size: int,
        ttl_seconds: int,
    ) -> None:
        self.session_id = session_id
        self._cache = cache
        self._max_cache_size = max_cache_size
        self._ttl_seconds = ttl_seconds

    async def get_items(self, limit: int | None = None) -> list[TResponseInputItem]:
        try:
            items = await self._cache.get(self.session_id, default=[])
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to load session {key}: {error}", key=self.session_id, error=str(exc))
            return []
        if not isinstance(items, list):
            return []
        if limit is not None:
            return items[-limit:]
        return items

    async def add_items(self, items: list[TResponseInputItem]) -> None:
        try:
            existing_items = await self._cache.get(self.session_id, default=[])
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to load session {key}: {error}", key=self.session_id, error=str(exc))
            return
        if not isinstance(existing_items, list):
            existing_items = []
        merged = existing_items + list(items)
        merged = self._trim_items(merged)
        await self._set_items(merged)

    async def pop_item(self) -> TResponseInputItem | None:
        try:
            items = await self._cache.get(self.session_id, default=[])
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to load session {key}: {error}", key=self.session_id, error=str(exc))
            return None
        if not isinstance(items, list) or not items:
            return None
        item = items.pop()
        await self._set_items(items)
        return item

    async def clear_session(self) -> None:
        try:
            await self._cache.delete(self.session_id)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to clear session {key}: {error}", key=self.session_id, error=str(exc))

    async def set_items(self, items: Iterable[TResponseInputItem]) -> None:
        merged = self._trim_items(list(items))
        await self._set_items(merged)

    def _trim_items(self, items: list[TResponseInputItem]) -> list[TResponseInputItem]:
        if len(items) > self._max_cache_size:
            return items[-self._max_cache_size :]
        return items

    async def _set_items(self, items: list[TResponseInputItem]) -> None:
        try:
            await self._cache.set(self.session_id, items, ttl=self._ttl_seconds)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to save session {key}: {error}", key=self.session_id, error=str(exc))
