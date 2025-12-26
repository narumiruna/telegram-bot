# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Core Development
- `uv sync` - Install/sync project dependencies
- `uv run playwright install chromium` - Install Playwright browser (required for some MCP servers)
- `uv run bot` - Start the Telegram bot (requires a `.env` file; see Environment Variables)
- `uv run bot --config config/default.json` - Start the bot with an explicit MCP server config

### Single Test Execution
- `uv run pytest tests/specific_test.py -v -s` - Run individual test file
- `uv run pytest tests/tools/test_yahoo_finance.py::test_function -v -s` - Run specific test function

### Quality Assurance
- `make lint` or `uv run ruff check src` - Run code linting
- `make type` or `uv run ty check src` - Run type checking
- `make test` or `uv run pytest -v -s --cov=src tests` - Run tests with coverage
- `make format` - Format code with ruff
- `make all` - Run format, lint, type check, and test in sequence

### Build and Publish
- `make publish` - Build wheel and publish to PyPI
- `uv build --wheel` - Build wheel package only

## Code Architecture

### Core Components

**Bot Framework**: Built on `python-telegram-bot` with callback-based handlers for different commands and message types.

**Agent System**: Uses `openai-agents` with MCP (Model Context Protocol) server integration for external tool access. The main agent is configured via `AgentCallback`.

**Configuration**: `-c/--config` points to an MCP server config JSON file (see `AgentCallback.load_mcp_config`).

The file must be a JSON object mapping server name to stdio server parameters, e.g.:

```json
{
  "firecrawl-mcp": {
    "command": "npx",
    "args": ["-y", "firecrawl-mcp"],
    "env": { "FIRECRAWL_API_KEY": "" }
  },
  "yfmcp": {
    "command": "uvx",
    "args": ["yfmcp@latest"]
  }
}
```

If a value in `env` is the empty string (`""`), the bot will replace it with the corresponding environment variable at runtime.

Note: `config/triage.json` exists but is not consumed by the current runtime path in `src/bot/bot.py`.

**Callbacks Structure**:
- `callbacks/` - Individual command handlers (format, translate, summarize, ticker, etc.)
- `callbacks/agent.py` - Main agent callback using OpenAI models with MCP tools
- Each callback handles specific Telegram commands and message processing

**Tools and Chains**:
- `tools/` - Utility functions for specific data sources:
  - `yahoo_finance.py` - Stock market data
  - `weblio.py` - Japanese dictionary integration
  - `wise.py` - Currency exchange rates
  - `duckduckgo.py` - Web search functionality
  - `mortgage.py` - Loan calculations
  - `tarot.py` - Tarot card readings
  - `monster_hunter_weapon.py` - Game weapon information
  - `award.py` - Achievement tracking
  - `content_extractor.py` - Web content extraction
  - `datetime.py` - Time utilities

- `chains/` - LLM-powered processing chains:
  - `translation.py` - Multi-language translation
  - `summary.py` - Text summarization
  - `jlpt/` - Japanese language learning system
  - `formatter.py` - Content formatting
  - `polisher.py` - Text improvement
  - `recipe.py` - Recipe generation
  - `product.py` - Product analysis
  - `keyword.py` - Keyword extraction
  - `notes.py` - Note processing

**Key Integration Points**:
- OpenAI models configured via environment variables (`OPENAI_MODEL`, `OPENAI_API_KEY`)
- Redis caching via `aiocache` for performance optimization and conversation memory
- Logfire integration for observability and monitoring
- Access control via `BOT_WHITELIST` environment variable
- Multi-platform content loading via `kabigon` library (PTT, Twitter, YouTube, Instagram, PDF)
- MCP server dependencies requiring Node.js (`npx`) and Python (`uvx`) package managers
- Retry mechanism using `tenacity` library with exponential backoff for robust API calls
- Lazy execution via `lazy.py` for simple agent tasks without full configuration

### Environment Requirements

The entrypoint (`src/bot/cli.py`) requires a `.env` file to exist (it uses `find_dotenv(..., raise_error_if_not_found=True)`), so local runs should include one.

**Essential Variables** (`.env` file):
- `BOT_TOKEN` - Telegram bot token
- `BOT_WHITELIST` - Comma-separated user IDs for access control
- `OPENAI_API_KEY` - OpenAI API key

**Model Configuration**:
- `OPENAI_MODEL` - Model name (default: `gpt-4.1`)
- `OPENAI_TEMPERATURE` - Model temperature (default: `0.0`)

**Alternative AI Providers**:
- `AZURE_OPENAI_API_KEY` - For Azure OpenAI integration
- `LITELLM_API_KEY` - If set, routes through LiteLLM via `openai-agents`
- `LANGFUSE_PUBLIC_KEY` - Langfuse observability platform
- `LANGFUSE_SECRET_KEY` - Langfuse secret key
- `LANGFUSE_HOST` - Langfuse host URL

**Infrastructure**:
- `CACHE_URL` - Redis cache URL (default: `redis://localhost:6379/0?pool_max_size=1`)
- `LOGFIRE_TOKEN` - Logfire observability token
- `DEVELOPER_CHAT_ID` - Chat ID for error reporting

**External Services**:
- `FIRECRAWL_API_KEY` - For web scraping via Firecrawl MCP server

## CICD & Testing Strategy

### CI/CD Pipelines

This repository uses GitHub Actions for continuous integration and deployment. Key workflows in `.github/workflows/`:

- **python.yml**: Main CI pipeline, runs on push/PR (main). Installs dependencies with uv, runs lint (ruff), tests (pytest + coverage), type-checks (ty), uploads coverage to Codecov.
- **deploy.yml**: Deploy workflow, triggered on main push/dispatch, stops old service, installs dependencies, sets up .env, copies files, starts the bot on self-hosted runner via launchctl (macOS).
- **bump-version.yml**: Manual semantic version bumper (major/minor/patch), tags the version using bump-my-version.
- **publish.yml**: Manual PyPI release workflow—builds a wheel with uv, publishes to PyPI using a secret token.

All workflows use uv as Python package/dependency manager and workflow/testing environment is based on Python 3.12.


Tests are located in `tests/` directory with structure mirroring `src/`. The codebase uses pytest with coverage reporting and type checking via ty.

### Development Workflow
1. Always run linting and type checking after code changes: `make lint && make type`
2. For new features, add corresponding tests in `tests/` with matching directory structure
3. Use `uv run pytest tests/path/to/test.py::test_function -v -s` for focused testing during development
4. When modifying retry behavior, ensure tools use `tenacity` library with proper error categorization
5. For agent modifications, validate the MCP config you changed is a plain server-name map (like `config/default.json`)

## Project Structure

- **Entry Point**: `src/bot/cli.py` - Main CLI interface using Typer
- **Bot Core**: `src/bot/bot.py` - Telegram bot setup and callback registration
- **Configuration**: `src/bot/config.py` - Loads and validates JSON configurations
- **Caching**: `src/bot/cache.py` - Redis-based caching with aiocache
- **Model Management**: `src/bot/model.py` - OpenAI model configuration and initialization
- **Retry System**: `src/bot/retry_utils.py` - Error handling and retry logic using tenacity
- **Lazy Execution**: `src/bot/lazy.py` - Simple agent tasks without full configuration

## Repo Conventions (for assistants)

- Prefer small, surgical changes; avoid unrelated refactors.
- Keep code compatible with Python 3.12+.
- Use `make format` (ruff) before committing formatting changes.
- Use `make lint`, `make type`, and focused `uv run pytest ...` runs to validate changes.
