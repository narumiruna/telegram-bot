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
- `uv run ruff check src` - Run code linting
- `uv run ty check src` - Run type checking
- `uv run pytest -v -s --cov=src tests` - Run tests with coverage
- `uv run ruff format` - Format code with ruff
- `uv run prek run -a` - Run pre-commit hooks on all files

### Build and Publish
- `uv build --wheel && uv publish` - Build wheel and publish to PyPI
- `uv build --wheel` - Build wheel package only

## Code Architecture

### Core Components

**Bot Framework**: Built on `python-telegram-bot` with callback-based handlers for different commands and message types.

**Agent System**: Uses `openai-agents` with MCP (Model Context Protocol) server integration for external tool access. The main agent is configured via `AgentCallback`.

**Configuration**: `-c/--config` points to an MCP server config JSON file (see `AgentCallback.load_mcp_config`).

The file must be a JSON object mapping server name to stdio server parameters. The default configuration (`config/default.json`) includes:

```json
{
  "playwright": {
    "command": "npx",
    "args": ["@playwright/mcp@latest"]
  },
  "firecrawl-mcp": {
    "command": "npx",
    "args": ["-y", "firecrawl-mcp"],
    "env": { "FIRECRAWL_API_KEY": "" }
  },
  "yfmcp": {
    "command": "uvx",
    "args": ["yfmcp@latest"]
  },
  "gurume": {
    "command": "uvx",
    "args": ["gurume@latest", "mcp"]
  }
}
```

If a value in `env` is the empty string (`""`), the bot will replace it with the corresponding environment variable at runtime.

**Note**: `config/triage.json` exists but is not loaded by default—you must explicitly specify it with `--config config/triage.json` to use it.

**Callbacks Structure**:
- `callbacks/` - Individual command handlers (format, translate, summarize, ticker, file_notes, etc.)
- `callbacks/base.py` - Unified callback architecture (CallbackProtocol, BaseCallback)
- `callbacks/agent.py` - Main agent callback using OpenAI models with MCP tools
- `callbacks/utils.py` - Shared utilities (safe_callback decorator, message processing)
- `callbacks/file_notes.py` - File upload handler for PDFs and HTML
- Each callback handles specific Telegram commands and message processing

**Callback Architecture** (unified as of 2025-12-27):

This codebase uses a **hybrid callback architecture** that supports both function-based and class-based patterns:

1. **CallbackProtocol** - Type-safe protocol that accepts both functions and classes
   ```python
   from src.bot.callbacks import CallbackProtocol
   # Both functions and callable classes conform to this protocol
   ```

2. **BaseCallback** - Optional abstract base class for stateful callbacks
   ```python
   from src.bot.callbacks import BaseCallback

   class MyCallback(BaseCallback):
       def __init__(self, config: str) -> None:
           self.config = config

       async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
           # Implementation using self.config
           pass
   ```

3. **Function-based callbacks** - For simple, stateless operations
   ```python
   from src.bot.callbacks.utils import safe_callback

   @safe_callback
   async def my_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
       # Simple implementation
       pass
   ```

**When to use each pattern**:

- **Function-based** (preferred for simplicity):
  - ✅ Stateless operations
  - ✅ Single responsibility
  - ✅ No shared logic needed
  - Examples: `summarize_callback`, `format_callback`, `echo_callback`

- **Class-based (BaseCallback)** (use when needed):
  - ✅ State management required (config, language settings, etc.)
  - ✅ Complex initialization logic
  - ✅ Shared methods or properties
  - Examples: `TranslationCallback` (manages target language), `HelpCallback` (manages help messages)

- **Special cases**:
  - `AgentCallback` does NOT inherit BaseCallback (uses `handle_command()` and `handle_reply()` methods instead of `__call__`)
  - `ErrorCallback` inherits BaseCallback (manages developer chat ID for error reporting)

**Callback utilities** (`callbacks/utils.py`):
- `@safe_callback` - Decorator for unified error handling (notifies users, logs errors)
- `get_processed_message_text()` - Extracts and processes message text, handles URL loading
- `get_message_text()` - Extracts raw text from messages
- `strip_command()` - Removes command prefix from message text

**Message Response Pattern** (`presentation.py`):

All callbacks should use `MessageResponse` for sending replies to ensure consistent handling of long messages:

```python
from src.bot.presentation import MessageResponse

# Create a response
response = MessageResponse(
    content="Your message content here",
    title="Optional Title",  # Used for Telegraph pages
    parse_mode="HTML"  # or None for plain text
)

# Send the response (automatically handles long messages)
await response.send(message)
```

**How it works**:
- Short messages (< 1000 chars): Sent directly via Telegram
- Long messages (≥ 1000 chars): Automatically creates a Telegraph page and sends the link

**When to use**:
- ✅ All user-facing text responses from callbacks
- ✅ LLM-generated content that might exceed Telegram's limits
- ✅ Formatted articles, summaries, translations

**Chain integration**:
- Chains should provide `.to_message_response()` methods that return `MessageResponse` instances
- Examples: `Summary.to_message_response()`, `Article.to_message_response()`

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

**File Processing**:
- `file_callback` (in `callbacks/__init__.py`) - Handles uploaded files (PDFs, HTML) and extracts content for processing

- `chains/` - LLM-powered processing chains:
  - `translation.py` - Multi-language translation
  - `summary.py` - Text summarization
  - `formatter.py` - Content formatting
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
6. When creating new callbacks:
   - Use function-based callbacks for simple, stateless operations (decorate with `@safe_callback`)
   - Use class-based callbacks (inherit from `BaseCallback`) only when state management is needed
   - Always implement the signature: `async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None`
   - Use `get_processed_message_text()` helper for consistent message text extraction and URL loading
   - Add tests in `tests/callbacks/` following existing patterns

## Project Structure

- **Entry Point**: `src/bot/cli.py` - Main CLI interface using Typer
- **Bot Core**: `src/bot/bot.py` - Telegram bot setup and callback registration
- **Configuration**: `src/bot/config.py` - Loads and validates JSON configurations
- **Constants**: `src/bot/constants.py` - Centralized constants (message lengths, cache TTL, etc.)
- **Caching**: `src/bot/cache.py` - Redis-based caching with aiocache (uses constants for TTL)
- **Model Management**: `src/bot/model.py` - OpenAI model configuration and initialization
- **Retry System**: `src/bot/retry_utils.py` - Error handling and retry logic using tenacity
- **Lazy Execution**: `src/bot/lazy.py` - Simple agent tasks without full configuration
- **Callbacks**: `src/bot/callbacks/` - Command handlers (see Callback Architecture above)
  - `base.py` - CallbackProtocol and BaseCallback
  - `utils.py` - Shared utilities (@safe_callback, message processing)
  - Individual handlers: `summarize.py`, `translate.py`, `format.py`, `ticker.py`, etc.

## Documentation

This repository maintains several documentation files for different purposes:

### CLAUDE.md (this file)
**Purpose**: Development guide for Claude Code (claude.ai/code) and AI assistants

**Contents**:
- Development commands and workflows
- Code architecture overview
- Callback patterns and conventions
- Environment requirements
- CI/CD pipelines
- Project structure
- Testing strategies

**Target audience**: AI assistants (Claude Code, GitHub Copilot), new developers

### Architecture Improvements

**Completed improvements (10/10 - 100%)**:
- ✅ #1: URL loading - Extracted common logic to `get_processed_message_text()` helper
- ✅ #2: Cache TTL - Set 1-week TTL to prevent unbounded growth
- ✅ #3: Error handling - Created `@safe_callback` decorator for unified error handling
- ✅ #4: Callback unification - Established `CallbackProtocol` and `BaseCallback`
- ✅ #5: Test coverage - Improved from 60% to 80% (+38 tests, 3 new test files)
- ✅ #6: Presentation layer - Created `MessageResponse` for UI separation
- ✅ #7: Constants - Centralized constants in `constants.py`
- ✅ #8: MCP timeout - Added 30s connect / 10s cleanup timeouts
- ✅ #9: Async optimization - Eliminated event loop blocking
- ✅ #10: Code quality - Adopted `match-case` pattern matching

**Note**: Detailed implementation history is available in git commit logs.

### README.md
**Purpose**: Public-facing project documentation

**Contents**:
- Project overview and features
- Installation instructions
- Environment variables configuration
- Available bot commands
- Basic project structure
- Testing commands

**Target audience**: End users, new contributors, GitHub visitors

### .github/copilot-instructions.md
**Purpose**: Redirect to CLAUDE.md

**Contents**: Single line pointing to CLAUDE.md

**Note**: GitHub Copilot reads this file for context, but the actual instructions are in CLAUDE.md

---

## Repo Conventions (for assistants)

- Prefer small, surgical changes; avoid unrelated refactors.
- Keep code compatible with Python 3.12+.
- Use `make format` (ruff) before committing formatting changes.
- Use `make lint`, `make type`, and focused `uv run pytest ...` runs to validate changes.
- Follow the established architecture patterns documented in this file (callbacks, presentation layer, error handling, etc.)
