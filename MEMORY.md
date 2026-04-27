# MEMORY

## GOTCHA

- `Message.answer(...)` 只會送到同一個 chat；要明確回覆到觸發訊息時，改用 `Message.reply(...)` 或帶 `reply_parameters` 的送法。
- 共享 response model 從 `answer()` 改成 `reply()` 時，要同步更新所有 callbacks 與測試的 awaited mocks，不然很容易出現 `'Mock' object can't be awaited`。
- callback 測試若會走到 `logfire.span(...)`，要在 `tests/conftest.py` 先設 `LOGFIRE_IGNORE_NO_CONFIG=1`，不然 pytest 會噴未設定 warning。

## TASTE

- 對共享的 Telegram response model，避免同時混用 `answer()` 與 `reply()` 介面；選定一種後，讓 callers 和 tests 一起跟上。
