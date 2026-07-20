# MEMORY

## GOTCHA

- `Message.answer(...)` 只會送到同一個 chat；要明確回覆到觸發訊息時，改用 `Message.reply(...)` 或帶 `reply_parameters` 的送法。
- 共享 response model 從 `answer()` 改成 `reply()` 時，要同步更新所有 callbacks 與測試的 awaited mocks，不然很容易出現 `'Mock' object can't be awaited`。
- callback 測試若會走到 `logfire.span(...)`，要在 `tests/conftest.py` 先設 `LOGFIRE_IGNORE_NO_CONFIG=1`，不然 pytest 會噴未設定 warning。
- TWSE 的 `pretty_repr()` 不會跳脫股票名稱內的 MarkdownV2 字元（例如 `國巨*`）；送 Telegram 前要先跳脫外部文字欄位，否則會出現 `can't parse entities`。
- `uv lock --upgrade` 可能為了新版 NumPy 回退到不支援目前 Python 的舊版 `numba`；保留受支援的 `numba` 下限，並在部署時明確傳入 Python 版本。

## TASTE

- 對共享的 Telegram response model，避免同時混用 `answer()` 與 `reply()` 介面；選定一種後，讓 callers 和 tests 一起跟上。
- Python 基準使用 3.14 以上；專案 metadata、本機開發、CI 與部署都要一致。
