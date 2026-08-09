# Repository Guidelines

## Project Structure & Module Organization
- `src/bot/` contains the Telegram bot implementation.
- `src/bot/agents/` contains LLM agents and conversation memory.
- `src/bot/callbacks/` holds Telegram command handlers (e.g., `summary.py`, `translate.py`).
- `src/bot/core/` contains prompt and response shaping.
- `src/bot/tools/` contains domain tools for awards, mortgages, tarot, Weblio, and Wise.
- `src/bot/utils/` contains shared utilities.
- `tests/` mirrors source structure with pytest-based coverage.
- `docs/CHANGELOG.md` records repository changes.

## Build, Test, and Development Commands
- `uv sync`: install dependencies into the uv-managed environment.
- `uv run bot`: start the bot using settings loaded from `.env`.
- `uv run pytest -v -s tests`: run the full test suite with verbose output.
- `uv run pytest -v -s --cov=src tests`: run tests with coverage reporting.
- `uv run ruff check src tests`: lint the codebase.
- `uv run ty check src tests`: run static type checks.
- `prek run -a`: run repository pre-commit hooks.

## Coding Style & Naming Conventions
- Python 3.14+, async-first design, and type hints everywhere.
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
- MCP servers are assembled in `src/bot/agents/chat.py` and controlled through environment settings.
- Keep secrets out of git history; use environment variables for tokens.

## Gotchas

- Symptom: `ty` reports `invalid-assignment` when tests assign `AsyncMock` directly to `callback.handle_message`.
  Root cause: Bound async methods have a concrete callable type, and direct `AsyncMock` attribute assignment violates the checker's attribute type constraints.
  Prevention: In tests, patch methods with `patch.object(..., new_callable=AsyncMock)` instead of direct reassignment.

- Symptom: Replying to a bot message with a URL causes the model input to lose the user's actual question or the replied context, so the agent answers only from fetched page content.
  Root cause: URL preprocessing replaced the whole composed message with `load_url()` output instead of appending fetched content after the original reply/current text.
  Prevention: Keep reply/current message blocks intact in the final user payload and append URL content as extra sections rather than substituting the prompt.

- Symptom: A Telegram response appears in the same chat but is not linked to the message that triggered it.
  Root cause: `Message.answer(...)` sends a regular chat message and does not establish a reply relationship unless reply parameters are supplied.
  Prevention: Use `Message.reply(...)` when responding directly to the triggering message, or pass `reply_parameters` explicitly.

- Symptom: Pytest shows `LogfireNotConfiguredWarning` when callback tests hit `logfire.span(...)`.
  Root cause: Tests call instrumented code paths without the app's normal `configure_logging()` startup, so Logfire stays unconfigured.
  Prevention: In test bootstrap, set `LOGFIRE_IGNORE_NO_CONFIG=1` so callback tests can run spans without warning noise.

- Symptom: Sending a bare command (e.g. `/f`) as a reply to a URL-only message silently does nothing.
  Root cause: `get_processed_message_text` early-exited with `(None, None)` when `current_message_text` was empty (command stripped), before ever reading `reply_to_message`.
  Prevention: Gather both current and reply texts before the empty-guard; only return early when both are empty.

- Symptom: A `@safe_callback` aiogram handler logs and re-raises errors but does not send the user-facing error reply.
  Root cause: aiogram dependency injection may call handlers with `message=...` as a keyword argument, so scanning only positional args misses the `Message`.
  Prevention: Error wrappers around aiogram handlers must check both positional args and the `message` keyword for `aiogram.types.Message`.

- Symptom: Deployment selects an ancient `numba` release that fails to build on the configured Python version.
  Root cause: `uv lock --upgrade` can backtrack to `numba` 0.53.1 when a newer NumPy exceeds current `numba` constraints, while that old release's metadata does not expose its runtime Python upper bound.
  Prevention: Keep a supported `numba` lower-bound constraint and make deployment pass the intended Python version explicitly to `uv sync`.

- Symptom: Sending a TWSE ticker whose name contains MarkdownV2 characters, such as `國巨*`, fails with `can't parse entities`.
  Root cause: `StockInfo.pretty_repr()` interpolates externally sourced names and symbols without escaping Telegram MarkdownV2 syntax.
  Prevention: Escape each external text field before passing a copied stock model to `pretty_repr()`.

- Symptom: An HTML conversion test expects ATX headings such as `# Notes` but receives Setext headings such as `Notes` followed by `=====`.
  Root cause: `markdownify` defaults can select Setext heading style, so asserting a guessed markdown representation couples the test to third-party formatting details.
  Prevention: When testing adapter wiring, mock `html_to_markdown` and assert the exact bytes passed; test formatting separately only against documented output guarantees.

## Taste

- Testing style preference: Prefer module-level pytest test functions; avoid class-based test containers such as `class TestQueryTickerCallback` unless explicitly requested.
- Agent memory preference: For single-agent chat flows, persist full `result.to_input_list()` items in memory (including tool-related items) and rely on process restart to reset state after tool changes.
- Telegram response preference: Use one interface for shared response models, currently `reply()`, and migrate callers and awaited test mocks together instead of mixing `answer()` and `reply()`.

## Changelog

- Append ONE line to the end of `docs/CHANGELOG.md`.
- Format: `YYYY-MM-DD | type(scope): summary (#ref)`.
- Do not modify existing content.
