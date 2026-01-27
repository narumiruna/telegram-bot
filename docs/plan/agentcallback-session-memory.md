# AgentCallback Redis Memory Evaluation and Plan

## Purpose
Evaluate whether `AgentCallback` can replace its Redis-based conversation cache with the Agents SDK session memory model, and outline a concrete migration plan.

## Current Behavior (Verified)
- `AgentCallback` stores full conversation history in Redis via `aiocache`.
- The cache key is `bot:{message_id}:{chat_id}`, so history is retrieved only when the user replies to a specific bot message.
- History is trimmed locally to `max_cache_size` and stored with a TTL.
- Tool-call items and fake ID items are removed before sending to the agent.

## Evaluation
### Feasibility
Yes. The Agents SDK session model can replace the manual cache flow because `Runner.run(..., session=...)` automatically persists and restores items. The SDK explicitly supports custom session implementations via `SessionABC`, which makes a Redis-backed session viable without changing the agent interface.

### Functional Differences to Address
- **Keying model:** Current behavior is per-reply-message. Sessions are typically per user/chat/thread. Switching to sessions changes how continuity is determined.
- **History filtering:** Current flow strips tool items before use. Sessions store all items by default; if tool messages must remain excluded, that behavior needs to be preserved or explicitly revised.
- **Trimming/compaction:** Current flow enforces `max_cache_size`. Sessions do not trim unless a compaction wrapper or custom logic is added.
- **TTL:** Current flow uses Redis TTL per cache entry. Session storage must explicitly apply TTL if the same retention behavior is required.

### Risk Summary
Medium. Behavior is likely to change for users who rely on the reply-to flow. The largest risk is accidentally broadening context (per-chat vs per-reply) and increasing token usage if trimming is not enforced.

## Plan
### Scope
Migrate only the conversation memory mechanism. No changes to agent instructions, message formatting, or tool integrations.

### Steps
1. **Define session identity rules**
   - Decide whether to keep per-reply semantics (session id derived from reply target) or switch to per-chat or per-thread.
   - Document the choice and its behavioral impact.
2. **Implement a Redis-backed Session**
   - Create a `RedisSession` that implements `SessionABC` using the existing `aiocache` client.
   - Store items under a stable session key with TTL.
   - Add trimming logic to enforce `max_cache_size` after `add_items`.
3. **Integrate with `AgentCallback`**
   - Replace manual `messages` collection + `Runner.run(..., input=...)` with `Runner.run(..., session=...)`.
   - Keep `remove_tool_messages` behavior only if explicitly required; otherwise allow full item history.
4. **Adjust tests**
   - Add unit tests for `RedisSession` behavior: `get_items`, `add_items`, `pop_item`, `clear_session`, and trimming.
   - Update `AgentCallback` tests to assert `Runner.run(..., session=...)` calls.
5. **Verification**
   - Run `uv run prek run -a` and resolve any failures.

## Non-Goals
- No change to message routing (commands/replies).
- No migration to OpenAI-hosted Conversations API.
- No introduction of new dependencies unless justified.

## Open Decisions
- Session scope: keep reply-scoped context (only replies to a bot message continue the same session).
- Tool message handling: keep removing tool messages to avoid cross-agent tool mismatch during handoff.
## Requirements (Confirmed)
- TTL: continue using `settings.cache_ttl_seconds`.
- max_cache_size: trim by item count only.
- pop/clear: not required for now.
- Filters: remove tool messages and `id == "__fake_id__"`.
- Redis failures: no fallback; skip persistence and retrieval when unavailable.
- Session key format: keep `bot:{message_id}:{chat_id}`.
* End Patch
