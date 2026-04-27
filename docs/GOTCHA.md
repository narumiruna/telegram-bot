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

- Symptom: After renaming shared Telegram response delivery from `answer()` to `reply()`, tests fail with `'Mock' object can't be awaited` or callbacks still call missing methods.
  Root cause: Callers and test doubles were only partially migrated, so some code still invoked `answer(message)` or mocked `message.answer` while the implementation awaited `message.reply`.
  Prevention: When changing a shared response method name, sweep all callbacks and tests together, including every awaited `Message` mock.

- Symptom: Pytest shows `LogfireNotConfiguredWarning` when callback tests hit `logfire.span(...)`.
  Root cause: Tests call instrumented code paths without the app's normal `configure_logging()` startup, so Logfire stays unconfigured.
  Prevention: In test bootstrap, set `LOGFIRE_IGNORE_NO_CONFIG=1` so callback tests can run spans without warning noise.
