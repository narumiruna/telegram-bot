"""Environment variable management."""

from __future__ import annotations

import os

# Bot settings
bot_token = os.getenv("BOT_TOKEN", "")
bot_whitelist = os.getenv("BOT_WHITELIST")
developer_chat_id = os.getenv("DEVELOPER_CHAT_ID")

# OpenAI / LLM settings
openai_model = os.getenv("OPENAI_MODEL", "gpt-4.1")
openai_temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.0"))
azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
litellm_api_key = os.getenv("LITELLM_API_KEY")

# Cache settings
cache_url = os.getenv("CACHE_URL", "redis://localhost:6379/0?pool_max_size=1")

# Observability settings
logfire_token = os.getenv("LOGFIRE_TOKEN")
langfuse_public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
langfuse_secret_key = os.getenv("LANGFUSE_SECRET_KEY")
langfuse_host = os.getenv("LANGFUSE_HOST")

firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")


def get_chat_ids() -> list[int] | None:
    """Parse whitelist string into list of chat IDs."""
    if not bot_whitelist:
        return None
    return [int(chat_id.strip()) for chat_id in bot_whitelist.replace(" ", "").split(",")]


def logfire_is_enabled() -> bool:
    """Check if Logfire monitoring is enabled."""
    return bool(logfire_token)


# from pydantic_settings import BaseSettings
# from pydantic_settings import SettingsConfigDict


# class Settings(BaseSettings):
#     bot_token: str
#     logfire_token: str | None = None

#     litellm_api_key: str
#     litellm_base_url: str
#     litellm_model: str

#     model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# settings = Settings()  # ty:ignore[missing-argument]
