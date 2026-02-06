from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
    )

    # Bot settings
    bot_token: str = Field(default="")
    bot_whitelist: str | None = Field(default=None)
    developer_chat_id: str | None = Field(default=None)

    # Agent settings
    agent_max_cache_size: int = Field(default=50)

    # OpenAI / LLM settings
    openai_model: str = Field(default="gpt-5-mini")
    openai_temperature: float = Field(default=0.0)
    azure_openai_api_key: str | None = Field(default=None)
    litellm_api_key: str | None = Field(default=None)

    # Cache settings
    cache_url: str = Field(default="memory://")
    cache_ttl_seconds: int = Field(default=604800)

    # Observability settings
    logfire_token: str | None = Field(default=None)

    # MCP settings
    mcp_connect_timeout: int = Field(default=30)
    mcp_cleanup_timeout: int = Field(default=10)
    mcp_server_timeout: int = Field(default=300)

    # Shutdown settings
    shutdown_timeout: int = Field(default=20)

    # UX settings
    max_message_length: int = Field(default=1000)

    # Other integrations
    firecrawl_api_key: str | None = Field(default=None)
    serpapi_api_key: str | None = Field(default=None)

    @property
    def chat_ids(self) -> list[int] | None:
        if not self.bot_whitelist:
            return None
        return [int(chat_id.strip()) for chat_id in self.bot_whitelist.replace(" ", "").split(",")]


settings = Settings()
