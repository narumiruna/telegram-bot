# Repository guidance

## Documentation

- Keep `README.md` and `.env.example` aligned whenever setup, commands, configuration, or environment variables change.
- Append exactly one line per requested repository change to `docs/CHANGELOG.md` using `YYYY-MM-DD | type(scope): summary (#ref)`; use `#internal` when no external reference exists and never edit existing lines.

## Code style

- Target Python 3.14 or newer.
- Use async APIs for I/O and type annotations throughout `src/`.
- Format and lint Python with Ruff, using the configured 120-character line limit and standard Python naming conventions.
- Keep each aiogram callback small and focused on one Telegram interaction.

## Commands

- Run `uv sync` to install or reconcile dependencies.
- Run `uv run bot` from the repository root with a populated `.env` to start the bot.
- Use `uv run pytest tests/<path>.py -v` for targeted tests.
- Run `just` to format `src/` and `tests/`, then lint, type-check, and run the coverage suite.
- Run `prek run -a` for the complete repository hook set.
- For documentation-only changes, `prek run --files <changed-paths>` and `git diff --check` are sufficient.

## Boundaries

- In message preprocessing, preserve both replied and current message text, append fetched URL content after those blocks, and treat input as empty only when both blocks are empty.
- Deliver shared Telegram response models through their async `reply()` methods; update callers and awaited test mocks together when delivery behavior changes.
- Keep `@safe_callback` compatible with `Message` passed either positionally or through the `message` keyword.
- Escape externally sourced TWSE names and symbols before passing them to `pretty_repr()` for Telegram MarkdownV2 output.
- Store per-chat memory from `result.to_input_list()` without flattening or dropping tool items; truncate only whole list items and rely on process restart to clear memory after tool changes.
- Preserve `numba>=0.65.1` in `pyproject.toml` and the explicit Python 3.14 deployment sync in `.github/workflows/deploy.yml`.
- Do not create or push release tags unless explicitly requested because tags matching `v*.*.*` trigger deployment.

## Security

- Keep local secrets in the ignored `.env` file, expose only placeholders through `.env.example`, and never put credentials in source, tests, logs, or Git history.
- Preserve `umask 077` and `chmod 600 .env` when changing deployment dotenv generation.

## Testing

- Use module-level pytest functions instead of class-based test containers unless explicitly requested.
- Patch concrete async methods with `patch.object(..., new_callable=AsyncMock)` instead of assigning `AsyncMock` directly.
- Keep `LOGFIRE_IGNORE_NO_CONFIG=1` in `tests/conftest.py` for tests that exercise Logfire spans without application startup.
- Place tests in the closest matching area under `tests/`; callback tests belong in `tests/callbacks/`.

## Project overview

- This repository is an async aiogram Telegram bot backed by OpenAI Agents.
- MCP servers are assembled in `src/bot/agents/chat.py`; Playwright and yfmcp are always configured, while Firecrawl and SerpAPI depend on environment settings.

## Repository structure

- `src/bot/agents/` owns LLM agents and conversation behavior.
- `src/bot/callbacks/` owns Telegram handlers and callback utilities.
- `src/bot/core/` owns prompt and response shaping.
- `src/bot/tools/` and `src/bot/utils/` own domain integrations and shared utilities.
- `tests/` mirrors source responsibilities with pytest coverage.
- `.github/workflows/` owns CI, version bumping, and deployment automation.

## Git and commits

- Use Conventional Commit subjects with a short imperative description, such as `fix(reply): retry Telegram network failures`.
- Keep automated version bump subjects in the form `Bump version: X → Y`.
- Use Conventional Commit pull request titles and summarize the outcome, checks run, and configuration changes in the description.
