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
