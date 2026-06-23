## Goal

Remove non-aiogram callback compatibility plumbing so command and file handlers accept `aiogram.types.Message` directly, with the same user-visible behavior and passing callback tests.

## Context

`src/bot/callbacks/utils.py` recognized `Update`, `context.args`, and `reply_text`-style objects even though the bot registers aiogram message handlers. The helper was used by ticker, file, and agent callbacks, so deleting it required updating those call sites together.

## Non-Goals

- Do not redesign callback routing or error reporting.
- Do not change command output, URL loading behavior, or article generation behavior.

## Plan

- [x] Replace `get_message_from_update` in `src/bot/callbacks/agent.py` by changing `handle_command` and `handle_reply` to accept `Message` directly; verified with `rg -n "get_message_from_update|Update" src/bot/callbacks/agent.py` returning no matches and `uv run pytest -v -s tests/callbacks/test_agent.py` passing.
- [x] Simplify `src/bot/callbacks/ticker.py` so `query_ticker_callback(message: Message)` parses symbols only from `message.text`; verified with updated `tests/callbacks/test_ticker.py` and `uv run pytest -v -s tests/callbacks/test_ticker.py` passing.
- [x] Simplify `src/bot/callbacks/file_notes.py` so `file_callback(message: Message, bot: Bot)` uses aiogram dependency injection and no `_get_bot`/`context`; verified with `tests/callbacks/test_file_notes.py` passing.
- [x] Delete cross-framework helpers from `src/bot/callbacks/utils.py`: `get_message_from_update`, `reply_text` recognition, and `Update` imports; kept `safe_callback` only smart enough to find an aiogram `Message` in direct or bound-method args; verified with `uv run pytest -v -s tests/callbacks/test_utils.py` passing.
- [x] Sweep imports and tests for stale compatibility references; verified with `rg -n "get_message_from_update|context\.args|reply_text|Message \| Update|Update" src tests` returning no matches.
- [x] Run quality gates for the touched surface; verified with `uv run ruff check src tests`, `uv run ty check src`, `prek run -a`, and `uv run pytest -v -s tests/callbacks/test_agent.py tests/callbacks/test_ticker.py tests/callbacks/test_utils.py tests/callbacks/test_file_notes.py tests/test_bot.py` passing.
- [x] Append a changelog line for the implemented cleanup in `docs/CHANGELOG.md`; verified with `tail -1 docs/CHANGELOG.md` returning `2026-06-23 | refactor(callbacks): remove non-aiogram callback plumbing (#internal)`.

## Risks

- `file_callback(message: Message, bot: Bot)` depends on aiogram DI injecting `Bot`; mitigated by `functools.wraps` preserving the unwrapped signature and `tests/callbacks/test_file_notes.py` verifying direct `Message`/`Bot` invocation.
- `safe_callback` decorates bound methods; mitigated by scanning positional args for `Message` and preserving agent bound-method tests.

## Completion Checklist

- [x] All aiogram callbacks touched by this plan expose `Message`-first signatures only, verified by `rg -n "Message \| Update|context\.args|get_message_from_update|reply_text" src/bot/callbacks` returning no matches.
- [x] Existing ticker, agent, utility, file-note, and bot tests pass with updated direct-`Message` test setup, verified by `uv run pytest -v -s tests/callbacks/test_agent.py tests/callbacks/test_ticker.py tests/callbacks/test_utils.py tests/callbacks/test_file_notes.py tests/test_bot.py`.
- [x] Static checks pass, verified by `uv run ruff check src tests`, `uv run ty check src`, and `prek run -a`.
- [x] `docs/CHANGELOG.md` contains one implementation changelog line for this cleanup, verified by `tail -1 docs/CHANGELOG.md`.
