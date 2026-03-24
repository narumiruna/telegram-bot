# GOTCHA

- Symptom: When writing Markdown content via shell heredoc, inline code markers around class names can appear to be malformed after complex quote escaping.
  Root cause: Mixing shell quote boundaries and Markdown backticks in one command makes it easy to misread the rendered command and assume data corruption.
  Prevention: After any heredoc write containing backticks/quotes, always validate persisted file content with `sed -n` before proceeding.
