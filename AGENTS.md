# Repository Guidelines

## Project Structure & Module Organization
- `src/bot/` contains the Telegram bot implementation.
- `src/bot/callbacks/` holds Telegram command handlers (e.g., `summary.py`, `translate.py`).
- `src/bot/chains/` includes LLM processing chains (formatting, summaries, notes).
- `src/bot/tools/` provides data-source integrations (Yahoo Finance, Wise, DuckDuckGo).
- `tests/` mirrors source structure with pytest-based coverage.
- `config/` stores MCP server configs such as `config/default.json`.
- `docs/` contains supplemental documentation.

## Build, Test, and Development Commands
- `uv sync`: install dependencies into the uv-managed environment.
- `uv run bot`: start the bot using `config/default.json`.
- `uv run bot --config config/custom.json`: start with a custom MCP config.
- `uv run pytest -v -s tests`: run the full test suite with verbose output.
- `uv run pytest -v -s --cov=src tests`: run tests with coverage reporting.
- `uv run ruff check src`: lint the codebase.
- `uv run ty check src`: run static type checks.
- `prek run -a`: run repository pre-commit hooks.

## Coding Style & Naming Conventions
- Python 3.13+, async-first design, and type hints everywhere.
- Follow PEP 8 with a 120-character line length (Ruff).
- Use `snake_case` for functions/variables, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants.
- Prefer single-responsibility modules and small, focused callbacks.

## Testing Guidelines
- Frameworks: `pytest`, `pytest-asyncio`, and `pytest-cov`.
- Test files use `test_*.py` and live under `tests/` with structure matching `src/`.
- Use `uv run pytest tests/<path>.py -v` for targeted runs.

## Commit & Pull Request Guidelines
- Commit messages are short, imperative, and sentence-cased (e.g., `Refactor settings`, `Add validation`).
- Version bumps use the format `Bump version: X → Y`.
- Pull requests should include:
  - A concise summary of changes.
  - Testing notes (commands run and results).
  - Configuration or `.env` updates when relevant.
  - Screenshots only if UI-facing behavior changes.

## Configuration & Secrets
- Local configuration lives in `.env` (see `README.md` for required keys).
- MCP servers are configured in `config/*.json`.
- Keep secrets out of git history; use environment variables for tokens.

## Agent-Specific Notes
- Review `CONSTITUTION.md` for non-negotiable constraints that apply to all changes.
