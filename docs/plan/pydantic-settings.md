# Pydantic Settings Migration Plan

## Goal
Consolidate environment variables and constants into a single `bot.settings` module using Pydantic Settings. The new module becomes the authoritative source for configuration and defaults. `env.py` and `constants.py` will be retired through a phased migration.

## Decisions
- Environment variables are case-insensitive (default Pydantic behavior).
- No prefix for environment variables.
- Global singleton: `settings = Settings()`.
- Langfuse settings are removed and must not be introduced.

## Target Module
- New file: `src/bot/settings.py`.
- `Settings` derives from `pydantic_settings.BaseSettings`.
- `SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")`.

## Field Mapping (No Langfuse)

### Bot
- `bot_token: str` (env: `BOT_TOKEN`)
- `bot_whitelist: str | None = None` (env: `BOT_WHITELIST`)
- `developer_chat_id: str | None = None` (env: `DEVELOPER_CHAT_ID`)

### LLM / Providers
- `openai_model: str = "gpt-4.1"` (env: `OPENAI_MODEL`)
- `openai_temperature: float = 0.0` (env: `OPENAI_TEMPERATURE`)
- `azure_openai_api_key: str | None = None` (env: `AZURE_OPENAI_API_KEY`)
- `litellm_api_key: str | None = None` (env: `LITELLM_API_KEY`)

### Cache
- `cache_url: str = "redis://localhost:6379/0?pool_max_size=1"` (env: `CACHE_URL`)
- `cache_ttl_seconds: int = 604800` (env: `CACHE_TTL_SECONDS`)

### Observability
- `logfire_token: str | None = None` (env: `LOGFIRE_TOKEN`)

### MCP
- `mcp_connect_timeout: int = 30` (env: `MCP_CONNECT_TIMEOUT`)
- `mcp_cleanup_timeout: int = 10` (env: `MCP_CLEANUP_TIMEOUT`)
- `mcp_server_timeout: int = 300` (env: `MCP_SERVER_TIMEOUT`)

### UX
- `max_message_length: int = 1000` (env: `MAX_MESSAGE_LENGTH`)

### Others
- `firecrawl_api_key: str | None = None` (env: `FIRECRAWL_API_KEY`)

### Computed Property
- `chat_ids: list[int] | None` derived from `bot_whitelist`.

## Migration Strategy (Phased)

### Phase 1: Add Settings Module (No Functional Changes)
- Create `src/bot/settings.py` with all fields above.
- Add `settings = Settings()` singleton.
- Do not modify other modules yet.

### Phase 2: Introduce Thin Compatibility Layers
- Update `src/bot/env.py` to re-export values from `settings`.
  - Example: `bot_token = settings.bot_token`.
- Update `src/bot/constants.py` to re-export values from `settings`.
  - Example: `MAX_MESSAGE_LENGTH = settings.max_message_length`.
- Keep existing import paths working to avoid large refactors.

### Phase 3: Incremental Call-Site Migration
- Replace call sites gradually:
  - `from bot.env import ...` -> `from bot.settings import settings`.
  - `from bot.constants import ...` -> `from bot.settings import settings`.
- Keep small, surgical changes per module.

### Phase 4: Cleanup
- Once no direct usage remains, remove `env.py` and `constants.py` or keep minimal forwarding stubs if needed.

## Testing Strategy
- Pydantic loads env at import time; avoid relying on the singleton in tests that mutate env.
- In tests that need env changes:
  - use `monkeypatch.setenv(...)` and instantiate `Settings()` directly.
- Avoid asserting against imported constants that may be fixed at import time.

## Non-Goals
- No introduction of new dependencies beyond Pydantic Settings.
- No changes to runtime behavior beyond configuration access refactor.
- No Langfuse keys or helpers.

## Open Questions
- Should `settings.py` expose helper functions or stay purely declarative?
- Do we want a deprecation window for `env.py` and `constants.py`?
