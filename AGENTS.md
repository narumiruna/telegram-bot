# Repository guidance

## Documentation

- Keep `README.md` and `.env.example` aligned when changing setup, commands, configuration, or environment variables.
- Append exactly one line to `docs/CHANGELOG.md` for each requested repository change using `YYYY-MM-DD | type(scope): summary (#ref)`.
- Never modify existing `docs/CHANGELOG.md` lines.

## Code style

- Target Python 3.14 or newer.
- Use async-first Python and type hints throughout `src/`.
- Follow Ruff with a 120-character line limit and standard Python naming conventions.
- Keep callbacks small and focused on one Telegram interaction.

## Commands

- Run `uv sync` to install or reconcile dependencies.
- Run `uv run bot` from the repository root with a populated `.env` to start the bot.
- Use `uv run pytest tests/<path>.py -v` for targeted tests.
- Run `just` for formatting, linting, type checking, and the coverage test suite.
- Run `prek run -a` for the complete repository hook set.
- For documentation-only changes, `prek run --files <changed-paths>` and `git diff --check` are sufficient.

## Boundaries

- Preserve both replied and current message text when adding fetched URL content, and treat input as empty only when both blocks are empty.
- Use `reply()` for shared Telegram response models and update callers plus awaited test mocks together when changing delivery behavior.
- Keep `@safe_callback` compatible with `Message` passed positionally or through the `message` keyword.
- Escape externally sourced TWSE names and symbols before formatting them as Telegram MarkdownV2.
- Persist complete `result.to_input_list()` items in per-chat agent memory and rely on process restart to reset memory after tool changes.
- Keep the supported `numba` lower bound in `pyproject.toml` and pass Python 3.14 explicitly during deployment sync.
- Do not create or push release tags unless explicitly requested because matching tags trigger deployment.

## Security

- Keep local secrets in the ignored `.env` file and expose documented placeholders only through `.env.example`.
- Keep tokens and integration credentials out of source, tests, logs, and Git history.
- Preserve restrictive deployment dotenv permissions through `umask 077` and `chmod 600`.

## Testing

- Use module-level pytest functions instead of class-based test containers unless explicitly requested.
- Patch concrete async methods with `patch.object(..., new_callable=AsyncMock)` instead of assigning `AsyncMock` directly.
- Keep `LOGFIRE_IGNORE_NO_CONFIG=1` in `tests/conftest.py` for tests that exercise Logfire spans without application startup.
- Put tests in the closest matching area under `tests/`; callback tests belong in `tests/callbacks/`.

## Project overview

- This repository is an async aiogram Telegram bot backed by OpenAI Agents.
- MCP servers are assembled in `src/bot/agents/chat.py`; Playwright and yfmcp are always enabled, while Firecrawl and SerpAPI depend on environment settings.

## Repository structure

- `src/bot/agents/` owns LLM agents and conversation behavior.
- `src/bot/callbacks/` owns Telegram handlers and callback utilities.
- `src/bot/core/` owns prompt and response shaping.
- `src/bot/tools/` and `src/bot/utils/` own domain integrations and shared utilities.
- `tests/` mirrors the source responsibilities with pytest coverage.
- `.github/workflows/` owns CI, version bumping, and deployment automation.

## Git and commits

- Use short, imperative, sentence-cased commit messages such as `Refactor settings`.
- Format version bump commits as `Bump version: X → Y`.
- Include a concise summary, checks run, and configuration changes in pull requests.
