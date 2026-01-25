# Repository Guidelines

**READ CONSTITUTION.md FIRST** - It defines non-negotiable rules with highest authority.

## Development Commands

### Core Development
- `uv sync` - Install/sync project dependencies
- `uv run playwright install chromium` - Install Playwright browser (required for MCP servers)
- `uv run bot` - Start the Telegram bot (requires `.env` file)
- `uv run bot --config config/default.json` - Start bot with explicit MCP config

### Testing
- `uv run pytest tests/specific_test.py -v -s` - Run individual test file
- `uv run pytest tests/tools/test_yahoo_finance.py::test_function -v -s` - Run specific test function
- `uv run pytest -v -s tests` - Run all tests

**Note**: Test results reflect behavior only when testing real system interactions, not mocked paths.

### Quality Assurance
- `uv run ruff check src` - Lint code
- `uv run ty check src` - Type check
- `uv run ruff format` - Format code
- `uv run prek run` - Run pre-commit hooks (REQUIRED after any change per CONSTITUTION.md)
- `uv run prek run -a` - Run pre-commit hooks on all files

### Build and Publish
- `uv build --wheel && uv publish` - Build wheel and publish to PyPI
- `uv build --wheel` - Build wheel package only

## Code Architecture

### Core Components

**Bot Framework**: Built on `python-telegram-bot` with callback-based handlers for commands and messages.

**Agent System**: Uses `openai-agents` with MCP (Model Context Protocol) server integration for external tool access via `AgentCallback`.

### Callback Architecture

Hybrid architecture supporting function-based and class-based patterns (unified 2025-12-27):

**Function-based callbacks** (preferred for simple, stateless operations):
```python
from src.bot.callbacks.utils import safe_callback

@safe_callback
async def my_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Simple implementation
    pass
```

**Class-based callbacks** (use when state management needed):
```python
from src.bot.callbacks import BaseCallback

class MyCallback(BaseCallback):
    def __init__(self, config: str) -> None:
        self.config = config

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Implementation using self.config
        pass
```

**Pattern selection**:
- Function-based: Stateless, single responsibility, no shared logic
- Class-based: State management, complex initialization, shared methods
- Special cases: `AgentCallback` (uses `handle_command()`/`handle_reply()`), `ErrorCallback` (manages developer chat ID)

**Callback utilities** (`callbacks/utils.py`):
- `@safe_callback` - Unified error handling decorator
- `get_processed_message_text()` - Message text extraction with URL loading
- `get_message_text()` - Raw message text extraction
- `strip_command()` - Command prefix removal

### Message Response Pattern

Use `MessageResponse` for consistent handling of long messages:

```python
from src.bot.presentation import MessageResponse

response = MessageResponse(
    content="Message content",
    title="Optional Title",  # For Telegraph pages
    parse_mode="HTML"  # or None for plain text
)

await response.send(message)
```

**Behavior**: Short messages (< 1000 chars) sent directly; long messages (≥ 1000 chars) create Telegraph page.

**Usage**: All user-facing responses, LLM-generated content, formatted articles.

### Modules

**Tools** (`tools/`): Data source utilities
- `yahoo_finance.py` - Stock market data
- `weblio.py` - Japanese dictionary
- `wise.py` - Currency exchange
- `duckduckgo.py` - Web search
- `mortgage.py` - Loan calculations
- `tarot.py` - Tarot readings
- `monster_hunter_weapon.py` - Game weapons
- `award.py` - Achievement tracking
- `content_extractor.py` - Web content extraction
- `datetime.py` - Time utilities

**Chains** (`chains/`): LLM-powered processing
- `translation.py` - Multi-language translation
- `summary.py` - Text summarization
- `formatter.py` - Content formatting
- `notes.py` - Note processing

**File Processing**: `file_callback` handles uploaded files (PDFs, HTML) and extracts content.

### Key Integrations

- OpenAI models via environment variables (`OPENAI_MODEL`, `OPENAI_API_KEY`)
- Redis caching via `aiocache` for performance and conversation memory
- Logfire for observability and monitoring
- Access control via `BOT_WHITELIST`
- Multi-platform content loading via `kabigon` (PTT, Twitter, YouTube, Instagram, PDF)
- MCP servers requiring Node.js (`npx`) and Python (`uvx`)
- Retry mechanism via `tenacity` with exponential backoff
- Lazy execution via `lazy.py` for simple agent tasks

## Environment Requirements

The entrypoint (`src/bot/cli.py`) requires a `.env` file to exist (uses `find_dotenv(..., raise_error_if_not_found=True)`).

**Essential Variables**:
- `BOT_TOKEN` - Telegram bot token
- `BOT_WHITELIST` - Comma-separated user IDs for access control
- `OPENAI_API_KEY` - OpenAI API key

**Model Configuration**:
- `OPENAI_MODEL` - Model name (default: `gpt-4.1`)
- `OPENAI_TEMPERATURE` - Model temperature (default: `0.0`)

**Alternative AI Providers**:
- `AZURE_OPENAI_API_KEY` - Azure OpenAI integration
- `LITELLM_API_KEY` - Routes through LiteLLM via `openai-agents`
- `LANGFUSE_PUBLIC_KEY` - Langfuse observability platform
- `LANGFUSE_SECRET_KEY` - Langfuse secret key
- `LANGFUSE_HOST` - Langfuse host URL

**Infrastructure**:
- `CACHE_URL` - Redis cache URL (default: `redis://localhost:6379/0?pool_max_size=1`)
- `LOGFIRE_TOKEN` - Logfire observability token
- `DEVELOPER_CHAT_ID` - Chat ID for error reporting

**External Services**:
- `FIRECRAWL_API_KEY` - Web scraping via Firecrawl MCP server

## CICD & Testing Strategy

### CI/CD Pipelines

GitHub Actions workflows in `.github/workflows/`:

- **python.yml**: Main CI pipeline (push/PR to main). Installs dependencies with uv, runs lint (ruff), tests (pytest), type-checks (ty), uploads coverage to Codecov.
- **deploy.yml**: Deploy workflow (main push/dispatch). Stops old service, installs dependencies, sets up .env, copies files, starts bot on self-hosted runner via launchctl (macOS).
- **bump-version.yml**: Manual semantic version bumper (major/minor/patch), tags version using bump-my-version.
- **publish.yml**: Manual PyPI release workflow—builds wheel with uv, publishes to PyPI using secret token.

All workflows use uv as Python package/dependency manager. Testing environment uses Python 3.12.

### Development Workflow
1. After any change, run `uv run prek run` per CONSTITUTION.md
2. For new features, add tests in `tests/` with matching directory structure
3. Use `uv run pytest tests/path/to/test.py::test_function -v -s` for focused testing during development
4. When modifying retry behavior, ensure tools use `tenacity` library with proper error categorization
5. For agent modifications, validate the MCP config you changed is a plain server-name map (like `config/default.json`)
6. When creating new callbacks:
   - Use function-based callbacks for simple, stateless operations (decorate with `@safe_callback`)
   - Use class-based callbacks (inherit from `BaseCallback`) only when state management is needed
   - Always implement the signature: `async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None`
   - Use `get_processed_message_text()` helper for consistent message text extraction and URL loading
   - Add tests in `tests/callbacks/` following existing patterns

## Project Structure & Module Organization

- `src/bot/`: main Python package (Telegram bot, CLI, config/env, caching, integrations).
- `tests/`: pytest suite mirroring package areas (e.g. `tests/callbacks/`, `tests/chains/`, `tests/tools/`).
- `config/`: MCP server JSON configs (the bot defaults to `config/default.json` unless overridden).
- `prompts/`: prompt assets used by LLM-powered chains.

Entry point: `bot = "bot.cli:main"` (see `pyproject.toml`).

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

## Coding Style & Naming Conventions

- Formatting/linting: `ruff` (line length: 120; import sorting forces single-line imports).
- Types: keep annotations accurate; prefer `ty`-clean code for new/modified modules.
- Naming: `snake_case` for functions/vars, `PascalCase` for classes, `test_*.py` for tests.

## Testing Guidelines

- Frameworks: `pytest`, `pytest-asyncio`.
- Prefer focused tests near the feature area (e.g. callback changes → `tests/callbacks/`).
- Use node ids for tight loops: `uv run pytest tests/tools/test_yahoo_finance.py::test_name -v -s`.

## Commit & Pull Request Guidelines

- Commits: follow the existing history—short, imperative subjects (e.g. "Fix …", "Add …"); keep one logical change per commit when possible.
- PRs: include a clear description, what changed/why, and how to test (commands + any required env vars). Add screenshots/snippets for user-facing formatting changes. Run `uv run prek run` before finalizing.

## Security & Configuration Tips

- Do not commit secrets. Use `.env` for `BOT_TOKEN`, `OPENAI_API_KEY`, and related credentials.
- Keep MCP config files free of hard-coded API keys; prefer environment variables.

## Documentation

This repository maintains several documentation files for different purposes:

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

### IMPROVEMENTS.md
**Purpose:** Strategic record of technical debt, improvement proposals, and implementation priorities.

Every core contributor must review IMPROVEMENTS.md before major refactors, architectural changes, or when setting development priorities.

**Scope:**
- Catalogs all significant improvement proposals, their status, responsible parties, and rationale.
- Ranks and tracks each item (Critical, Operational, Strategic, Developer Experience).
- Roadmap for ongoing and planned technical, operational, and architectural upgrades.

**Maintenance:**
- Update whenever work on a tracked issue starts, status changes, or a proposal completes.
- Treat all roadmap and prioritization efforts as subordinate to CONSTITUTION.md constraints. If a conflict arises, constitutional constraints override.

**Reference:**
- IMPROVEMENTS.md sets the roadmap; AGENTS.md governs implementation; README.md summarizes for users and new contributors.


### .github/copilot-instructions.md
**Purpose**: Redirect to AGENTS.md

**Contents**: Single line pointing to AGENTS.md

**Note**: GitHub Copilot reads this file for context, but the actual instructions are in AGENTS.md

---

## Repo Conventions (for assistants)

- Prefer small, surgical changes; avoid unrelated refactors.
- Keep code compatible with Python 3.12+.
- Use `uv run prek run` before committing changes.
- Follow the established architecture patterns documented in this file (callbacks, presentation layer, error handling, etc.)
