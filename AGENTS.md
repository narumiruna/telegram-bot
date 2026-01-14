# Repository Guidelines

## Constitution (Read First)

`CONSTITUTION.md` defines the project’s highest-priority, non-negotiable rules and is immutable. Follow it for any work in this repo, and avoid duplicating its foundational rules in other docs.

## Project Structure & Module Organization

- `src/bot/`: main Python package (Telegram bot, CLI, config/env, caching, integrations).
- `tests/`: pytest suite mirroring package areas (e.g. `tests/callbacks/`, `tests/chains/`, `tests/tools/`).
- `config/`: MCP server JSON configs (the bot defaults to `config/default.json` unless overridden).
- `prompts/`: prompt assets used by LLM-powered chains.

Entry point: `bot = "bot.cli:main"` (see `pyproject.toml`).

## Build, Test, and Development Commands

This repo uses `uv` + Python 3.12.

- `uv sync`: install/sync dependencies.
- `uv run bot`: run the bot (requires `.env` in repo root).
- `uv run bot --config config/default.json`: run with an explicit MCP config.
- `uv run pytest -v -s --cov=src tests`: run all tests with coverage.
- `uv run ruff check src`: lint (autofix is enabled in pre-commit).
- `uv run ruff format`: format code.
- `uv run ty check src`: type-check.
- `uv run prek run -a`: run pre-commit hooks over the whole repo.

## Coding Style & Naming Conventions

- Formatting/linting: `ruff` (line length: 120; import sorting forces single-line imports).
- Types: keep annotations accurate; prefer `ty`-clean code for new/modified modules.
- Naming: `snake_case` for functions/vars, `PascalCase` for classes, `test_*.py` for tests.

## Testing Guidelines

- Frameworks: `pytest`, `pytest-asyncio`, `pytest-cov`.
- Prefer focused tests near the feature area (e.g. callback changes → `tests/callbacks/`).
- Use node ids for tight loops: `uv run pytest tests/tools/test_yahoo_finance.py::test_name -v -s`.

## Commit & Pull Request Guidelines

- Commits: follow the existing history—short, imperative subjects (e.g. “Fix …”, “Add …”); keep one logical change per commit when possible.
- PRs: include a clear description, what changed/why, and how to test (commands + any required env vars). Add screenshots/snippets for user-facing formatting changes. Verify required workflows in `CONSTITUTION.md` are satisfied.

## Security & Configuration Tips

- Do not commit secrets. Use `.env` for `BOT_TOKEN`, `OPENAI_API_KEY`, and related credentials.
- Keep MCP config files free of hard-coded API keys; prefer environment variables.
