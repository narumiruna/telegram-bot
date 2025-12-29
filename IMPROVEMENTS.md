# Bot 架構改進追蹤

此文件追蹤專案架構改進的狀態與待辦事項。

**最後更新**: 2025-12-29
**進度**: 8/10 完成 (80%)

---

## 📊 快速狀態總覽

| 優先級 | 問題 | 影響範圍 | 狀態 |
|--------|------|----------|------|
| 🔴 Critical | 1. URL 載入重複 | 可維護性 | ✅ 2025-12-27 |
| 🔴 Critical | 2. Cache 無界增長 | 穩定性、效能 | ✅ 2025-12-27 |
| 🔴 Critical | 3. 錯誤靜默失敗 | 用戶體驗 | ✅ 2025-12-27 |
| 🔴 Critical | 4. Callback 模式不一致 | 可維護性 | ✅ 2025-12-27 |
| ⚠️ Important | 5. 測試覆蓋不完整 | 品質保證 | 🔕 暫不處理 |
| ⚠️ Important | 6. UI 邏輯混入 | 關注點分離 | ✅ 2025-12-29 |
| ⚠️ Important | 7. 常數重複定義 | 可維護性 | ✅ 2025-12-27 |
| ⚠️ Important | 8. MCP Timeout | 穩定性 | ✅ 2025-12-29 |
| 💡 Nice-to-have | 9. Async 優化 | 效能 | ✅ 2025-12-29 |
| 💡 Nice-to-have | 10. 程式碼品質 | 可讀性 | ⬜ 待處理 |

---

## ✅ 已完成項目

已完成的改進項目已整合到專案架構中。詳細的實作說明和使用指引請參考：
- **Callback 架構**: 參見 `CLAUDE.md` > Code Architecture > Callback Architecture
- **Message Response Pattern**: 參見 `CLAUDE.md` > Code Architecture > Message Response Pattern
- **變更歷史**: 使用 `git log` 查看提交記錄

### 完成項目摘要

- **Issue #1** (2025-12-27): 抽取 URL 載入邏輯到 `get_processed_message_text()` helper
- **Issue #2** (2025-12-27): 設定 Cache TTL 為 1 週，防止記憶體無限增長
- **Issue #3** (2025-12-27): 建立 `@safe_callback` 裝飾器統一錯誤處理
- **Issue #4** (2025-12-27): 建立 `CallbackProtocol` 和 `BaseCallback` 統一 callback 架構
- **Issue #6** (2025-12-29): 建立 `MessageResponse` 抽取 presentation layer
- **Issue #7** (2025-12-27): 建立 `constants.py` 集中管理常數
- **Issue #8** (2025-12-29): 為 MCP 連線和清理操作添加 timeout 控制
- **Issue #9** (2025-12-29): 確認 async 模式正確性，消除事件循環阻塞

---

## ⬜ 待處理項目

### 🔕 Issue #5: 測試覆蓋不完整 (暫不處理)

**說明**: 許多 chains 只是備用功能，未被 bot 實際使用，因此暫不需要提升測試覆蓋率。核心功能的測試覆蓋已足夠。

**未測試模組**:
- `src/bot/chains/product.py`
- `src/bot/chains/polisher.py`
- `src/bot/chains/recipe.py`
- `src/bot/chains/keyword.py`
- `src/bot/chains/notes.py`

**缺少的測試類型**:
- 端到端 Telegram 訊息流程測試
- Cache 行為測試（TTL、淘汰、並發）
- MCP server 整合測試
- Retry 邏輯行為測試

**建議** (若未來需要):
1. 為每個 chain 新增基本單元測試
2. 使用 `pytest-telegram` 或 mock 建立整合測試
3. 新增 `tests/integration/` 目錄

**目標覆蓋率**: 80%+

---

### 💡 Issue #10: 程式碼品質提升

**小型改進**:
- 使用 `match-case` 取代多層 if-elif（Python 3.10+，提升可讀性）
- 型別註解完整性檢查（`ty check --strict` mode，更嚴格的型別檢查）

**注意**: Import 順序已由 ruff (isort) 自動處理，`make format` 會自動修正

---

## 📝 備註

- 已完成的改進項目不會從此文件中移除，以保持歷史追蹤
- 新的架構規範已整合到 `CLAUDE.md` 中，供開發者參考
- 詳細的實作過程可透過 git 提交記錄查看
- 每個 issue 實作前應先撰寫測試
- 遵循專案的 linting、type checking 標準

---

## 🎯 下一步

1. **Issue #10**: 評估是否需要程式碼品質提升（match-case、strict type checking）
2. **持續優化**: 效能監控、文件補充
3. **新功能開發**: 遵循已建立的架構規範（參見 `CLAUDE.md`）
