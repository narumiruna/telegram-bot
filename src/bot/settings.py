"""Centralized configuration using Pydantic Settings."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_ignore_empty=True,
        extra="ignore",
    )

    # Bot settings
    bot_token: str = Field(default="", validation_alias="BOT_TOKEN")
    bot_whitelist: str | None = Field(default=None, validation_alias="BOT_WHITELIST")
    developer_chat_id: str | None = Field(default=None, validation_alias="DEVELOPER_CHAT_ID")

    # Agent settings
    agent_max_cache_size: int = Field(default=50, validation_alias="AGENT_MAX_CACHE_SIZE")

    # OpenAI / LLM settings
    openai_model: str = Field(default="gpt-5-mini", validation_alias="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.0, validation_alias="OPENAI_TEMPERATURE")
    azure_openai_api_key: str | None = Field(default=None, validation_alias="AZURE_OPENAI_API_KEY")
    litellm_api_key: str | None = Field(default=None, validation_alias="LITELLM_API_KEY")

    # Cache settings
    cache_url: str | None = Field(default=None, validation_alias="CACHE_URL")
    cache_ttl_seconds: int = Field(default=604800, validation_alias="CACHE_TTL_SECONDS")

    # Observability settings
    logfire_token: str | None = Field(default=None, validation_alias="LOGFIRE_TOKEN")

    # MCP settings
    mcp_connect_timeout: int = Field(default=30, validation_alias="MCP_CONNECT_TIMEOUT")
    mcp_cleanup_timeout: int = Field(default=10, validation_alias="MCP_CLEANUP_TIMEOUT")
    mcp_server_timeout: int = Field(default=300, validation_alias="MCP_SERVER_TIMEOUT")

    # Shutdown settings
    shutdown_timeout: int = Field(default=20, validation_alias="SHUTDOWN_TIMEOUT")

    # UX settings
    max_message_length: int = Field(default=1000, validation_alias="MAX_MESSAGE_LENGTH")

    # Other integrations
    firecrawl_api_key: str | None = Field(default=None, validation_alias="FIRECRAWL_API_KEY")
    serpapi_api_key: str | None = Field(default=None, validation_alias="SERPAPI_API_KEY")

    @property
    def chat_ids(self) -> list[int] | None:
        if not self.bot_whitelist:
            return None
        return [int(chat_id.strip()) for chat_id in self.bot_whitelist.replace(" ", "").split(",")]


settings = Settings()
