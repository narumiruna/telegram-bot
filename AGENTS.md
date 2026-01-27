# Repository Guidelines

## Project Structure & Module Organization
- `src/bot/`: main bot package (aiogram v3, callbacks, chains, tools, integrations).
- `src/bot/callbacks/`: command handlers and utilities.
- `src/bot/chains/`: LLM-powered processing (summary/translation/formatting).
- `src/bot/tools/`: data source helpers (finance, search, etc.).
- `tests/`: pytest suite mirroring the package layout (e.g., `tests/callbacks/`).

## Build, Test, and Development Commands
- `uv sync`: install/sync dependencies.
- `uv run bot`: run the Telegram bot (requires `.env`).
- `uv run pytest -v -s tests`: run full test suite.
- `uv run pytest tests/path/to/test.py::test_name -v -s`: run a focused test.
- `uv run ruff check src`: lint.
- `uv run ruff format`: format.
- `uv run ty check src`: type check.
- `uv run prek run -a`: run all pre-commit hooks (required by CONSTITUTION.md).

## Coding Style & Naming Conventions
- Python 3.12+.
- Formatting/linting via Ruff (line length 120; single-line imports).
- Naming: `snake_case` for functions/vars, `PascalCase` for classes, `test_*.py` for tests.
- Prefer small, surgical changes; avoid unrelated refactors.

## Testing Guidelines
- Frameworks: `pytest`, `pytest-asyncio`.
- Tests should reflect real behavior; avoid over-mocking.
- Keep tests close to feature area (e.g., callback changes → `tests/callbacks/`).

## Commit & Pull Request Guidelines
- Commits: short, imperative subjects (“Fix …”, “Add …”), one logical change per commit.
- PRs: describe what/why, include test commands and required env vars; add screenshots for user-facing formatting changes.

## Security & Configuration Tips
- Do not commit secrets. Use `.env` for `BOT_TOKEN`, `OPENAI_API_KEY`, and related keys.
- MCP configuration is environment-based; keep config files free of hard-coded secrets.

## Callback & Response Patterns
- Use function-based callbacks for stateless handlers; class-based only when state is needed.
- Use `MessageResponse` for user-facing output; long messages auto-expand via Telegraph.
