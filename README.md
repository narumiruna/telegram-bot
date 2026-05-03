# Narumi's Telegram Bot

A Telegram bot built with [aiogram](https://github.com/aiogram/aiogram) and [OpenAI Agents](https://github.com/openai/openai-agents-python).  
Provides chat assistance, URL summarization, translation, article rewriting, finance lookups, and YouTube search via a set of slash commands.

## Requirements

- Python `>=3.13`
- [`uv`](https://github.com/astral-sh/uv)

## Quick Start

```sh
# 1. Install dependencies
uv sync

# 2. Create .env (see Environment Variables below)
cp .env.example .env
# edit .env and fill in BOT_TOKEN and model access credentials

# 3. Run the bot
uv run bot
```

The CLI requires `.env` in the working directory and will fail immediately if it is missing.

## Environment Variables

**Required:**

```plaintext
BOT_TOKEN=your_telegram_bot_token
```

**Required for LLM features — choose one mode:**

```plaintext
# Option A: direct OpenAI
OPENAI_API_KEY=your_openai_api_key

# Option B: OpenAI-compatible proxy (e.g. local Bifrost)
OPENAI_BASE_URL=http://127.0.0.1:8080/openai/v1
# OPENAI_API_KEY can be empty when the proxy does not require it
```

**Optional:**

```plaintext
BOT_WHITELIST=comma,separated,chat_ids   # restrict access to specific chat IDs
DEVELOPER_CHAT_ID=123456789              # receives error notifications

OPENAI_MODEL=gpt-5-mini
OPENAI_TEMPERATURE=0.0
AGENT_MAX_CACHE_SIZE=50
MAX_MESSAGE_LENGTH=1000

MCP_CONNECT_TIMEOUT=30
MCP_CLEANUP_TIMEOUT=10
MCP_SERVER_TIMEOUT=300
SHUTDOWN_TIMEOUT=20

FIRECRAWL_API_KEY=...    # enables Firecrawl MCP
SERPAPI_API_KEY=...      # enables SerpAPI MCP
LOGFIRE_TOKEN=...        # enables Logfire observability
```

See `.env.example` for a complete template.

## Commands

| Command | Description |
|---|---|
| `/help` | Show built-in help |
| `/a`, `/gpt` | Chat with the agent |
| `/model` | Show the current model |
| `/setmodel <name>` | Set model at runtime (`gpt-4.1`, `gpt-5-mini`, `gpt-5-nano`, `gpt-5.1-codex-mini`, `gpt-5.3-codex`, `gpt-5.4`) |
| `/s` | Summarize a URL |
| `/jp`, `/tc`, `/en` | Translate message text to Japanese, Traditional Chinese, or English |
| `/t` | Query ticker data (Yahoo Finance + TWSE) |
| `/yt` | Search YouTube |
| `/f`, `/w` | Rewrite text into article format |
| `/echo` | Echo the message |

**Additional interactions:**
- Replying to a bot message routes the reply to the chat agent.
- Sending a `.pdf` or `.html` file triggers rewrite processing.

## MCP Configuration

MCP servers are configured in `config/*.json`. The default config is loaded automatically:

```sh
uv run bot                              # uses config/default.json
uv run bot --config config/custom.json  # uses a custom config
```

**Always-enabled MCP servers:** `playwright`, `yfmcp`  
**Optional MCP servers** (activated when the corresponding API key is set): Firecrawl (`FIRECRAWL_API_KEY`), SerpAPI (`SERPAPI_API_KEY`)

## Project Layout

```text
src/bot/
  agents/        # LLM agents and conversation memory
  callbacks/     # Telegram command handlers
  core/          # prompt and response shaping
  tools/         # external data integrations
  utils/         # shared utilities
  bot.py         # dispatcher and routing
  cli.py         # CLI entrypoint
  settings.py    # Pydantic settings (reads from .env)
tests/           # pytest suite (mirrors src/bot/ structure)
config/          # MCP server config files
docs/            # project documentation
```

## Development

```sh
uv run ruff check src   # lint
uv run ty check src     # type check
prek run -a             # run all pre-commit hooks
```

## Testing

```sh
uv run pytest -v -s tests                # full test suite
uv run pytest -v -s --cov=src tests      # with coverage
uv run pytest tests/<path>.py -v         # single file
```

## License

MIT. See [`LICENSE`](LICENSE).
