# Narumi's Telegram Bot

A Telegram bot built on aiogram and OpenAI Agents. It supports chat-based assistance, document summarization, translation, article-style rewriting, and market data lookups. The bot is async-first and loads configuration from a required `.env` file.

## Features
- Chat agent with optional MCP servers (yfmcp always, Firecrawl/SerpAPI when configured).
- Summarize URLs or documents via `/s`.
- Translate text to Japanese, Traditional Chinese, or English.
- Rewrite content into a structured article-style response.
- Yahoo Finance and TWSE ticker lookup.
- PDF/HTML file ingestion for rewriting.

## Requirements
- Python `>=3.13`
- `uv` for dependency management

## Quick Start
```sh
uv sync
uv run bot
```

## Configuration
The app loads `.env` at startup and will fail if it is missing. Required and common settings:

```plaintext
BOT_TOKEN=your_telegram_bot_token

# Optional
BOT_WHITELIST=comma,separated,chat_ids
OPENAI_MODEL=gpt-5-mini
CACHE_URL=memory://  # use redis://... for Redis-backed memory
FIRECRAWL_API_KEY=...
SERPAPI_API_KEY=...
AZURE_OPENAI_API_KEY=...
LITELLM_API_KEY=...
LOGFIRE_TOKEN=...
DEVELOPER_CHAT_ID=...
```

## Bot Commands
- `/help` show built-in help.
- `/a`, `/gpt` chat with the agent.
- `/s` summarize a URL or document content.
- `/jp`, `/tc`, `/en` translate text.
- `/t` query tickers (Yahoo Finance + TWSE).
- `/yt` search YouTube.
- `/f`, `/w` rewrite text into a structured article.
- `/echo` echo the message.

## Project Structure
```
src/bot/
  agents/        # LLM agents (chat, summary, translation, writer)
  callbacks/     # Telegram command handlers
  core/          # Article + prompt templates
  tools/         # External data tools (finance, search, etc.)
  utils/         # Shared utilities (chunking, retry, url helpers)
  bot.py         # Dispatcher + routing
  cli.py         # CLI entrypoint (loads .env)
  settings.py    # Pydantic settings
  memory.py      # aiocache-backed session store

tests/           # pytest suite
```

## Development
- Lint: `uv run ruff check src`
- Type check: `uv run ty check src`
- Pre-commit: `prek run -a`

## Testing
```sh
uv run pytest -v -s tests
uv run pytest -v -s --cov=src tests
```

## License
MIT. See `LICENSE`.
