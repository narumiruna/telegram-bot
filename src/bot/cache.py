from functools import cache
from typing import Final

from aiocache import BaseCache
from aiocache import Cache
from loguru import logger

from .settings import settings

DEFAULT_REDIS_URL: Final[str] = "redis://localhost:6379/0?pool_max_size=1"
DEFAULT_MEMORY_URL: Final[str] = "memory://"


@cache
def get_cache_from_env() -> BaseCache:
    url = settings.cache_url
    if not url:
        logger.warning("No cache url provided, using {url}", url=DEFAULT_REDIS_URL)
    return Cache.from_url(url)
