# Narumi's Telegram Bot

A sophisticated Telegram bot powered by advanced language models that provides intelligent text processing, content analysis, and information retrieval capabilities. The bot supports multiple features including text polishing, summarization, translation, and financial data retrieval.

## Features

### Core Capabilities
- **AI Agent**: Intelligent agent powered by OpenAI models with MCP (Model Context Protocol) integration
- **Content Formatting**: Automatically organize and format text content with proper structure
- **Summarization**: Generate concise summaries with reasoning chains, insights, and hashtags
- **Translation**: Translate text between multiple languages with contextual understanding
- **Research Notes**: Create structured research reports from text content

### Data & Tools
- **Financial Data**: Real-time stock market information via Yahoo Finance
- **Currency Exchange**: Live exchange rates from Wise
- **Web Search**: DuckDuckGo integration for web searches
- **Content Loading**: Support for URLs, PDFs, HTML files, and YouTube transcripts (via kabigon library)

### Architecture Highlights
- **80% Test Coverage**: 245+ comprehensive tests ensuring reliability
- **Unified Callback System**: Protocol-based architecture supporting both function and class-based callbacks
- **Error Handling**: Automatic error reporting with user-friendly messages
- **Caching**: Redis-based caching with TTL for performance optimization
- **Message Response Layer**: Automatic handling of long messages via Telegraph
- **Access Control**: Whitelist-based user authentication for security

## Table of Contents

- [Features](#features)
- [Environment Variables](#environment-variables)
- [Installation](#installation)
- [Usage](#usage)
- [Commands](#commands)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Development](#development)
- [Testing](#testing)
- [License](#license)

## Environment Variables

Create a `.env` file in the root directory of your project with the following variables:

### Essential Variables

```plaintext
# Telegram Bot Configuration
BOT_TOKEN=your_telegram_bot_token
BOT_WHITELIST=comma_separated_user_ids

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini  # or gpt-4.1, gpt-4o, etc.
OPENAI_TEMPERATURE=0.0
```

### Optional Variables

```plaintext
# Redis Cache (default: redis://localhost:6379/0?pool_max_size=1)
CACHE_URL=redis://localhost:6379/0?pool_max_size=1

# Observability
LOGFIRE_TOKEN=your_logfire_token

# Error Reporting
DEVELOPER_CHAT_ID=your_telegram_chat_id

# External Services
FIRECRAWL_API_KEY=your_firecrawl_api_key  # For web scraping via MCP

# Alternative AI Providers
AZURE_OPENAI_API_KEY=your_azure_key
LITELLM_API_KEY=your_litellm_key
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=your_langfuse_host
```

See [AGENTS.md](AGENTS.md#environment-requirements) for detailed configuration options.

## Installation

### Prerequisites

- Python 3.12 or higher
- Redis server (for caching)
- Node.js and npm (for MCP servers)

### Steps

1. Install uv (Python package manager):
```sh
pip install uv
```

2. Clone the repository and install dependencies:
```sh
git clone <repository-url>
cd bot
uv sync
```

3. Install Playwright browser (for some MCP servers):
```sh
uv run playwright install chromium
```

4. Install optional dependencies:
   - [SingleFile CLI](https://github.com/gildas-lormeau/single-file-cli?tab=readme-ov-file#manual-installation) for web page archiving

5. Create a `.env` file with your configuration (see [Environment Variables](#environment-variables))

## Usage

### Start the Bot

Default configuration (uses `config/default.json`):
```sh
uv run bot
```

With custom MCP server configuration:
```sh
uv run bot --config config/custom.json
```

### MCP Server Configuration

The bot uses MCP (Model Context Protocol) servers for extended capabilities. Configure servers in a JSON file:

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

See [AGENTS.md](AGENTS.md#configuration) for more details.

## Commands

### Available Commands

- `/help` - Display available commands and usage information
- `/summarize` - Generate concise summaries with reasoning chains, insights, and hashtags
- `/translate` - Translate text to specified languages (supports multiple languages)
- `/format` - Format and organize text content with proper structure
- `/ticker` - Retrieve real-time financial data for stock symbols
- `/echo` - Echo back the message (for testing)

### AI Agent

Send any message to the bot without a command to interact with the AI agent, which has access to:
- Web search (DuckDuckGo)
- Financial data (Yahoo Finance)
- Currency exchange rates (Wise)
- Content extraction from URLs
- And more via MCP servers

### File Support

The bot can process uploaded files:
- **PDF files**: Extracts text content and formats it
- **HTML files**: Parses and formats HTML content

## Project Structure

```
src/bot/
├── callbacks/         # Telegram command handlers
│   ├── agent.py      # Main AI agent with MCP integration
│   ├── base.py       # Callback architecture (Protocol & BaseCallback)
│   ├── utils.py      # Shared utilities (@safe_callback, message processing)
│   ├── format.py     # Text formatting
│   ├── summary.py    # Content summarization
│   ├── translate.py  # Translation services
│   └── ticker.py     # Financial data retrieval
├── chains/           # LLM-powered processing chains
│   ├── formatter.py  # Content formatting chain
│   ├── notes.py      # Research notes generation
│   ├── summary.py    # Summary generation
│   └── translation.py # Translation chain
├── tools/            # Utility tools for specific data sources
│   ├── yahoo_finance.py # Stock market data
│   ├── wise.py       # Currency exchange rates
│   ├── duckduckgo.py # Web search
│   └── ...
├── bot.py            # Telegram bot setup and callback registration
├── cli.py            # Command-line interface
├── config.py         # MCP server configuration
├── constants.py      # Centralized constants
├── cache.py          # Redis-based caching
├── presentation.py   # MessageResponse for UI layer
├── model.py          # OpenAI model configuration
├── utils.py          # Utility functions
└── lazy.py           # Simple agent tasks

tests/                # Test suite (80% coverage, 245+ tests)
├── callbacks/        # Callback tests
├── chains/           # Chain tests (notes, formatter, summary)
├── tools/            # Tool tests
└── ...

config/               # MCP server configurations
└── default.json      # Default MCP server setup
```

See [AGENTS.md](AGENTS.md) for detailed architecture documentation.

## Documentation

This project maintains comprehensive documentation for different audiences:

- **[AGENTS.md](AGENTS.md)** - Development guide for AI assistants and developers
  - Code architecture and patterns
  - Development commands and workflows
  - Callback patterns and conventions
  - Environment requirements
  - CI/CD pipelines
  - Completed architecture improvements (10/10 - 100%)

- **README.md** (this file) - Public-facing project documentation
  - Quick start guide
  - Features overview
  - Basic usage instructions

**Note**: Detailed implementation history and architecture improvement details are available in git commit logs and AGENTS.md.

## Development

### Getting Started

1. Install pre-commit hooks:
```sh
pre-commit install
```

2. Follow code style guidelines:
   - Use type hints (built-in types: `list[X]`, `dict[K, V]`, `X | None`)
   - Write docstrings for functions and classes
   - Follow PEP 8 guidelines
   - Use `match-case` for pattern matching (Python 3.10+)

3. Create feature branches for new development:
```sh
git checkout -b feature/your-feature-name
```

### Architecture Guidelines

When creating new callbacks:
- **Function-based** (preferred for simplicity): Use for stateless operations
- **Class-based** (inherit from `BaseCallback`): Use when state management is needed
- Always use `@safe_callback` decorator for error handling
- Use `get_processed_message_text()` helper for message text extraction
- Use `MessageResponse` for sending replies (handles long messages automatically)

See [AGENTS.md](AGENTS.md) for detailed architecture documentation.

## Testing

The project maintains **80% test coverage** with 245+ tests across the codebase.

Run the test suite:

```sh
# Run all tests
uv run pytest -v -s tests

# Run with coverage report
uv run pytest -v -s --cov=src tests

# Run specific test file
uv run pytest tests/chains/test_notes.py -v

# Run with coverage and HTML report
uv run pytest --cov=src --cov-report=html tests
```

### Quality Assurance

```sh
# Run linting
make lint
# or
uv run ruff check src

# Run type checking
make type
# or
uv run ty check src

# Run all checks (format, lint, type, test)
make all
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
