"""Environment variable compatibility layer."""

from __future__ import annotations

from .settings import settings

# Bot settings
bot_token = settings.bot_token
bot_whitelist = settings.bot_whitelist
developer_chat_id = settings.developer_chat_id

# OpenAI / LLM settings
openai_model = settings.openai_model
openai_temperature = settings.openai_temperature
azure_openai_api_key = settings.azure_openai_api_key
litellm_api_key = settings.litellm_api_key

# Cache settings
cache_url = settings.cache_url

# Observability settings
logfire_token = settings.logfire_token

firecrawl_api_key = settings.firecrawl_api_key


def get_chat_ids() -> list[int] | None:
    """Parse whitelist string into list of chat IDs."""
    return settings.chat_ids
