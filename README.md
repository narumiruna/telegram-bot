# Narumi's Telegram Bot

A Telegram bot built with aiogram and OpenAI Agents.
It provides chat assistance, URL summarization, translation, article rewriting, and finance lookups.

## Requirements
- Python `>=3.13`
- `uv`

## Quick Start
1. Create `.env` in the project root.
2. Install dependencies.
3. Run the bot.

```sh
uv sync
uv run bot
```

## Environment Variables
The CLI requires `.env` to exist and will fail fast if the file is missing.

Required:

```plaintext
BOT_TOKEN=your_telegram_bot_token
```

Model access:

```plaintext
# Option A: direct OpenAI
OPENAI_API_KEY=your_openai_api_key

# Option B: OpenAI-compatible proxy (for example local Bifrost)
OPENAI_BASE_URL=http://127.0.0.1:8080/openai/v1
# OPENAI_API_KEY can be empty when your proxy does not require it
```

Common optional variables:

```plaintext
BOT_WHITELIST=comma,separated,chat_ids
OPENAI_MODEL=gpt-5-mini
OPENAI_TEMPERATURE=0.0
AGENT_MAX_CACHE_SIZE=50
MAX_MESSAGE_LENGTH=1000
MCP_CONNECT_TIMEOUT=30
MCP_CLEANUP_TIMEOUT=10
MCP_SERVER_TIMEOUT=300
SHUTDOWN_TIMEOUT=20
FIRECRAWL_API_KEY=...
SERPAPI_API_KEY=...
LOGFIRE_TOKEN=...
DEVELOPER_CHAT_ID=...
```

## Commands
- `/help`: show built-in help.
- `/a` or `/gpt`: chat with the agent.
- `/model`: show the current model.
- `/setmodel <model_name>`: set model at runtime (`gpt-4.1`, `gpt-5-mini`, `gpt-5-nano`, `gpt-5.1-codex-mini`, `gpt-5.3-codex`, `gpt-5.4`).
- `/s`: summarize a URL.
- `/jp`, `/tc`, `/en`: translate message text.
- `/t`: query ticker data (Yahoo Finance + TWSE).
- `/yt`: search YouTube.
- `/f` or `/w`: rewrite text into article format.
- `/echo`: echo the message.

Also supported:
- Replying to a bot message routes to the chat agent flow.
- Sending `.pdf` or `.html` files triggers rewrite processing.

## MCP Integrations
- Always enabled: `playwright`, `yfmcp`.
- Optional: Firecrawl MCP (`FIRECRAWL_API_KEY`), SerpAPI MCP (`SERPAPI_API_KEY`).

## Project Layout
```text
src/bot/
  agents/        # LLM agents
  callbacks/     # Telegram command handlers
  core/          # prompt and response shaping
  tools/         # external data integrations
  utils/         # shared utilities
  bot.py         # dispatcher and routing
  cli.py         # CLI entrypoint
  settings.py    # pydantic settings
tests/           # pytest suite
config/          # MCP config assets
docs/            # project docs
```

## Development
```sh
uv run ruff check src
uv run ty check src
prek run -a
```

## Testing
```sh
uv run pytest -v -s tests
uv run pytest -v -s --cov=src tests
```

## License
MIT. See `LICENSE`.
