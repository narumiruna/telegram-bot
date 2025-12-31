# Repository Guidelines

## Project Structure & Module Organization

- `src/` contains application code with two packages: `bot/` (Telegram bot runtime) and `kabigon/` (content loaders/tools).
- `tests/` mirrors `src/` with unit and integration tests (e.g., `tests/callbacks/`, `tests/tools/`).
- `config/` holds MCP server configs (e.g., `config/default.json`).
- `prompts/` contains YAML prompt assets used by chains.

## Build, Test, and Development Commands

- `uv sync` installs/syncs dependencies for Python 3.12+.
- `uv run bot` starts the bot (requires a `.env` file).
- `make format` runs `ruff format` across the repo.
- `make lint` runs `ruff check`.
- `make type` runs `ty check src`.
- `make test` runs `pytest -v -s --cov=src tests`.
- `make all` runs format, lint, type check, and tests in sequence.

## Coding Style & Naming Conventions

- Python 3.12+, `src/` layout, type hints required.
- Formatting and linting: `ruff` with line length 120.
- Use `snake_case` for functions/variables, `PascalCase` for classes, and `test_*.py` for tests.
- Prefer concise, readable async code; keep callbacks small and focused.

## Testing Guidelines

- Framework: `pytest` with `pytest-cov`.
- Keep tests alongside existing structure (e.g., `tests/tools/test_*.py` mirrors `src/bot/tools/`).
- Run a single test: `uv run pytest tests/tools/test_yahoo_finance.py -v -s`.
- Coverage target: maintain or improve existing coverage baseline.

## Commit & Pull Request Guidelines

- Commit messages are imperative and may use lightweight prefixes (e.g., `refactor:`, `update`, `Add`).
- Keep commits scoped; avoid bundling unrelated changes.
- PRs should include: a short description, testing notes (commands run), and config/env changes if applicable.

## Environment & Configuration

- A `.env` file is required for local runs; include `BOT_TOKEN`, `BOT_WHITELIST`, and `OPENAI_API_KEY`.
- MCP server configuration lives in `config/*.json`. When changing configs, mention the target file in PR notes.
