# GOTCHA

- Symptom: When writing Markdown content via shell heredoc, inline code markers around class names can appear to be malformed after complex quote escaping.
  Root cause: Mixing shell quote boundaries and Markdown backticks in one command makes it easy to misread the rendered command and assume data corruption.
  Prevention: After any heredoc write containing backticks/quotes, always validate persisted file content with `sed -n` before proceeding.

- Symptom: `gh pr create --body "..."` unexpectedly runs shell commands and fails with `command not found`.
  Root cause: Backticks in a double-quoted shell argument trigger command substitution before `gh` receives the body text.
  Prevention: For PR text containing Markdown-like tokens, write content to a temp file and use `gh pr create --body-file`.

- Symptom: `ty` reports `invalid-assignment` when tests assign `AsyncMock` directly to `callback.handle_message`.
  Root cause: Bound async methods have a concrete callable type, and direct `AsyncMock` attribute assignment violates the checker's attribute type constraints.
  Prevention: In tests, patch methods with `patch.object(..., new_callable=AsyncMock)` instead of direct reassignment.

- Symptom: Replying to a bot message with a URL causes the model input to lose the user's actual question or the replied context, so the agent answers only from fetched page content.
  Root cause: URL preprocessing replaced the whole composed message with `load_url()` output instead of appending fetched content after the original reply/current text.
  Prevention: Keep reply/current message blocks intact in the final user payload and append URL content as extra sections rather than substituting the prompt.

- Symptom: Sending a bare command (e.g. `/f`) as a reply to a URL-only message silently does nothing.
  Root cause: `get_processed_message_text` early-exited with `(None, None)` when `current_message_text` was empty (command stripped), before ever reading `reply_to_message`.
  Prevention: Gather both current and reply texts before the empty-guard; only return early when both are empty.
