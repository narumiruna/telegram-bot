# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Core Development
- `uv run bot` - Start the Telegram bot with default configuration
- `uv run bot -c config/triage.json` - Start bot with alternative configuration (multi-agent setup)
- `uv sync` - Install/sync project dependencies

### Single Test Execution
- `uv run pytest tests/specific_test.py -v -s` - Run individual test file
- `uv run pytest tests/tools/test_yahoo_finance.py::test_function -v -s` - Run specific test function

### Quality Assurance
- `make lint` or `uv run ruff check src` - Run code linting
- `make type` or `uv run mypy --install-types --non-interactive src` - Run type checking
- `make test` or `uv run pytest -v -s --cov=src tests` - Run tests with coverage
- `make cover` - Run tests with XML coverage report

### Build and Publish
- `make publish` - Build wheel and publish to PyPI
- `uv build --wheel` - Build wheel package only

## Code Architecture

### Core Components

**Bot Framework**: Built on `python-telegram-bot` with callback-based handlers for different commands and message types.

**Agent System**: Uses `openai-agents` library with MCP (Model Context Protocol) server integration for external tool access. The main agent is configured via `AgentCallback` class.

**Configuration**: JSON-based configuration in `config/` directory determines bot behavior:

- `default.json` - Standard single-agent mode with MCP server tools:
  - `firecrawl-mcp` - Web scraping capabilities
  - `yfmcp` - Yahoo Finance market data
  - `twsemcp` - Taiwan Stock Exchange data

- `triage.json` - Multi-agent orchestration system using OpenAI Agents handoff pattern:
  - `triage_agent` - Main routing agent that delegates to specialists
  - `thinking_agent` - Logic and reasoning specialist (responds in Traditional Chinese)
  - `browser_agent` - Web browsing with Playwright MCP server
  - `financial_agent` - Stock/finance specialist with Yahoo Finance + Taiwan Stock Exchange tools
  - `reading_agent` - Document processing and summarization with fetch MCP server

**Callbacks Structure**:
- `callbacks/` - Individual command handlers (format, translate, summarize, ticker, etc.)
- `callbacks/agent.py` - Main agent callback using OpenAI models with MCP tools
- Each callback handles specific Telegram commands and message processing

**Tools and Chains**:
- `tools/` - Utility functions for specific data sources:
  - `yahoo_finance.py` - Stock market data
  - `twrate.py` - Taiwan exchange rate history
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
  - `jlpt/` - Japanese language learning system (v1, v2, v3 prompts)
  - `formatter.py` - Content formatting
  - `polisher.py` - Text improvement
  - `recipe.py` - Recipe generation
  - `product.py` - Product analysis
  - `keyword.py` - Keyword extraction
  - `notes.py` - Note processing

**Key Integration Points**:
- OpenAI models configured via environment variables (`MODEL`, `OPENAI_API_KEY`)
- Redis caching via `aiocache` for performance optimization
- Logfire integration for observability and monitoring
- Access control via `BOT_WHITELIST` environment variable
- Multi-platform content loading via `kabigon` library (PTT, Twitter, YouTube, Instagram, PDF)
- MCP server dependencies requiring Node.js (`npx`) and Python (`uvx`) package managers

### Environment Requirements

**Essential Variables** (`.env` file):
- `BOT_TOKEN` - Telegram bot token
- `BOT_WHITELIST` - Comma-separated user IDs for access control
- `OPENAI_API_KEY` - OpenAI API key

**Model Configuration**:
- `MODEL` - OpenAI model name (default: `gpt-4o-mini`)
- `OPENAI_MODEL` - Specific model override (default: `gpt-4o`)
- `OPENAI_TEMPERATURE` - Model temperature (default: `0.0`)

**Alternative AI Providers**:
- `AZURE_OPENAI_API_KEY` - For Azure OpenAI integration
- `LANGFUSE_PUBLIC_KEY` - Langfuse observability platform
- `LANGFUSE_SECRET_KEY` - Langfuse secret key
- `LANGFUSE_HOST` - Langfuse host URL

**Infrastructure**:
- `CACHE_URL` - Redis cache URL (default: `redis://localhost:6379/0?pool_max_size=1`)
- `LOGFIRE_TOKEN` - Logfire observability token
- `DEVELOPER_CHAT_ID` - Chat ID for error reporting

**External Services**:
- `FIRECRAWL_API_KEY` - For web scraping via Firecrawl MCP server

## Testing Strategy

Tests are located in `tests/` directory with structure mirroring `src/`. The codebase uses pytest with coverage reporting and type checking via mypy.

### Development Workflow
1. Always run linting and type checking after code changes: `make lint && make type`
2. For new features, add corresponding tests in `tests/` with matching directory structure
3. Use `uv run pytest tests/path/to/test.py::test_function -v -s` for focused testing during development

## Project Structure

- **Entry Point**: `src/bot/cli.py` - Main CLI interface using Typer
- **Bot Core**: `src/bot/bot.py` - Telegram bot setup and callback registration
- **Configuration**: `src/bot/config.py` - Loads and validates JSON configurations
- **Caching**: `src/bot/cache.py` - Redis-based caching with aiocache
- **Model Management**: `src/bot/model.py` - OpenAI model configuration and initialization
