# Remove env.py and constants.py Plan

## Goal
Remove `src/bot/env.py` and `src/bot/constants.py` and use `src/bot/settings.py` as the single source of configuration.

## Scope
- Update all imports and references that still depend on `env.py` or `constants.py`.
- Remove the two files after all call sites migrate.
- Keep behavior identical, including defaults and environment variable mapping.

## Assumptions
- `src/bot/settings.py` already exists and contains all fields used by the current codebase.
- No Langfuse settings should be introduced.

## Migration Steps
1. Inventory remaining imports:
   - Find all `from bot.env` / `from bot.constants` imports in `src/` and `tests/`.
2. Replace usage:
   - Convert `MAX_MESSAGE_LENGTH` → `settings.max_message_length`.
   - Convert `CACHE_TTL_SECONDS` → `settings.cache_ttl_seconds`.
   - Convert `MCP_*` timeouts → `settings.mcp_*` equivalents.
3. Tests update:
   - Replace constant imports with `from bot.settings import settings`.
   - Keep assertions verifying default values, now against `settings`.
4. Remove files:
   - Delete `src/bot/env.py` and `src/bot/constants.py`.
5. Verification:
   - Run `uv run prek run -a` and fix any formatting or lint issues.

## Non-Goals
- No behavioral changes to the bot runtime.
- No refactor of settings schema beyond what is required for removal.

## Risks
- Tests or modules that rely on module-level constants might import early; ensure changes don’t introduce import-time side effects.
- Default values must remain identical; validate by comparing the previous constants with `settings` defaults.

## Success Criteria
- No code references to `env.py` or `constants.py` remain.
- Tests pass with the same defaults and behavior as before.
- `src/bot/env.py` and `src/bot/constants.py` are removed.
