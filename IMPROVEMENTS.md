# Bot 架構改進建議

根據架構分析（2025-12-27），以下是發現的問題與改進建議，按優先級排序。

## 🔴 高優先級（Critical）

### 1. 代碼重複 - URL 載入邏輯
**問題**：`summarize.py`、`translate.py`、`format.py`、`file_notes.py` 重複相同的 URL 解析和載入模式。

**影響範圍**：
- `src/bot/callbacks/summarize.py:27-29`
- `src/bot/callbacks/translate.py:31-33`
- `src/bot/callbacks/format.py:26-28`
- `src/bot/callbacks/file_notes.py` (間接使用)

**重複代碼**：
```python
url = parse_url(message_text)
if url:
    message_text = await async_load_url(url)
```

**建議方案**：
1. **裝飾器方案**：建立 `@with_url_loading` 裝飾器，自動處理 URL 載入
2. **前處理器方案**：統一的 `preprocess_message()` 函數
3. **基類方案**：抽象 `BaseMessageCallback` 類，提供 `get_processed_text()` 方法

**優先推薦**：裝飾器方案，最小侵入性。

---

### 2. Cache 無界增長
**問題**：對話快取無 TTL、無淘汰策略，會無限累積。

**位置**：`src/bot/callbacks/agent.py:177-212`

**具體問題**：
- 快取 key：`f"bot:{message_id}:{chat_id}"`，每則訊息獨立 key
- 無過期時間設定
- 無記憶體上限
- 對話上下文碎片化（只有回覆該訊息時才載入）

**建議方案**：
```python
# 1. 設定 TTL
await self.cache.set(cache_key, messages, ttl=86400)  # 24 hours

# 2. 改用 chat-based key 維持連續對話
cache_key = f"bot:chat:{chat_id}"

# 3. 實作 LRU 淘汰
# 使用 Redis EXPIRE 或 cachetools.LRUCache
```

**影響**：穩定性、記憶體使用、用戶體驗。

---

### 3. 錯誤處理靜默失敗
**問題**：多處捕捉例外後只記錄 log，用戶不知道發生錯誤。

**位置**：
- `src/bot/callbacks/ticker.py:34-36`
- `src/bot/callbacks/summarize.py`
- `src/bot/callbacks/format.py`
- `src/bot/callbacks/agent.py` 快取載入失敗

**目前行為**：
```python
except Exception as e:
    logger.error("Failed: {error}", error=str(e))
    # 沒有通知用戶
```

**建議方案**：
```python
async def safe_callback(callback_func):
    """統一錯誤處理裝飾器"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            return await callback_func(update, context)
        except SpecificError as e:
            await update.message.reply_text(f"處理失敗：{e}")
            logger.error("Error in {func}: {error}", func=callback_func.__name__, error=str(e))
        except Exception as e:
            await update.message.reply_text("發生未預期的錯誤，請稍後再試")
            logger.exception("Unexpected error in {func}", func=callback_func.__name__)
    return wrapper
```

---

### 4. Callback 模式不一致
**問題**：混用函數式和類別式 callback，缺乏統一介面。

**現況**：
- **函數**：`summarize_callback`, `format_callback`, `echo_callback`, `ticker_callback`
- **類別**：`TranslationCallback`, `AgentCallback`, `HelpCallback`, `ErrorCallback`

**建議方案**：
1. **定義 Protocol**：
```python
from typing import Protocol

class CallbackProtocol(Protocol):
    async def __call__(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None: ...
```

2. **或抽象基類**：
```python
from abc import ABC, abstractmethod

class BaseCallback(ABC):
    @abstractmethod
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """處理訊息"""
        pass

    async def get_message_text(self, message: Message) -> str | None:
        """統一的訊息文字提取"""
        pass

    async def handle_url_if_present(self, text: str) -> str:
        """統一的 URL 處理"""
        pass
```

3. **遷移策略**：逐步將函數式 callback 改為類別，或全部改為函數。

---

## ⚠️ 中優先級（Important）

### 5. 測試覆蓋不完整
**問題**：部分 chain 實作未測試，缺少整合測試。

**未測試模組**：
- `src/bot/chains/product.py`
- `src/bot/chains/polisher.py`
- `src/bot/chains/recipe.py`
- `src/bot/chains/keyword.py`
- `src/bot/chains/notes.py`

**缺少的測試類型**：
- 端到端 Telegram 訊息流程測試
- Cache 行為測試（TTL、淘汰、並發）
- MCP server 整合測試
- Retry 邏輯行為測試

**建議**：
1. 為每個 chain 新增基本單元測試
2. 使用 `pytest-telegram` 或 mock 建立整合測試
3. 新增 `tests/integration/` 目錄

**目標覆蓋率**：80%+

---

### 6. UI 邏輯混入業務層
**問題**：Telegraph 頁面建立、`MAX_MESSAGE_LENGTH` 判斷散落在業務邏輯中。

**位置**：
- `src/bot/chains/summary.py` - Telegraph 整合
- `src/bot/chains/translation.py` - Telegraph 整合
- `src/bot/chains/formatter.py` - Telegraph 整合
- `src/bot/callbacks/*.py` - 長度判斷與格式化

**建議方案**：
1. **抽取 Presentation Layer**：
```python
# src/bot/presentation.py
from dataclasses import dataclass

@dataclass
class MessageResponse:
    content: str
    title: str | None = None

    async def send(self, message: Message) -> None:
        """自動判斷是否需要建立 Telegraph 頁面"""
        if len(self.content) > MAX_MESSAGE_LENGTH:
            url = create_page(
                title=self.title or "Response",
                html_content=self.content.replace("\n", "<br>")
            )
            await message.reply_text(url)
        else:
            await message.reply_text(self.content)
```

2. **統一回覆介面**：所有 callback 回傳 `MessageResponse` 物件。

---

### 7. 常數重複定義 ✅ **已修復**
~~**問題**：`MAX_LENGTH = 1_000` 在三個檔案中重複定義。~~

**修復內容**：
- 建立 `src/bot/constants.py` 集中管理常數
- 定義 `MAX_MESSAGE_LENGTH: Final[int] = 1_000`
- 修改 `translate.py`, `format.py`, `file_notes.py` 導入常數

**驗證**：✅ Lint 通過，✅ Type check 通過

---

### 8. MCP 連線缺少 Timeout 管理
**問題**：MCP server 連線只有 `client_session_timeout_seconds`，缺少明確超時處理。

**位置**：`src/bot/callbacks/agent.py:88-112`

**建議方案**：
1. **連線池模式**：
```python
class MCPConnectionPool:
    def __init__(self, max_connections: int = 5, timeout: float = 30.0):
        self.max_connections = max_connections
        self.timeout = timeout
        self._pool: dict[str, MCPClient] = {}

    async def get_client(self, server_name: str) -> MCPClient:
        """取得或建立 MCP client，帶 timeout"""
        if server_name not in self._pool:
            self._pool[server_name] = await asyncio.wait_for(
                self._connect(server_name),
                timeout=self.timeout
            )
        return self._pool[server_name]
```

2. **Circuit Breaker 模式**：連線失敗達閾值後暫停重試。

3. **健康檢查**：定期 ping MCP servers。

---

## 💡 低優先級（Nice-to-have）

### 9. Async 模式優化
**觀察**：
- `async_wrapper()` 在 `utils.py` 定義但未使用
- Telegraph 操作是同步的（阻塞 async context）
- `get_composed_loader()` 全域快取（thread-safe 疑慮）

**建議**：
1. 移除未使用的 `async_wrapper()`
2. 為 Telegraph 操作使用 `asyncio.to_thread()`
3. 評估 loader 快取的並發安全性

---

### 10. 程式碼品質提升
**小型改進**：
- 使用 `match-case` 取代多層 if-elif（Python 3.10+，提升可讀性）
- 型別註解完整性檢查（`ty check --strict` mode，更嚴格的型別檢查）

**注意**：Import 順序已由 ruff (isort) 自動處理，`make format` 會自動修正

---

## 📊 優先級排序總結

| 優先級 | 問題 | 影響範圍 | 工作量 | 狀態 |
|--------|------|----------|--------|------|
| 🔴 Critical | 1. URL 載入重複 | 可維護性 | 中 | ✅ 2025-12-27 |
| 🔴 Critical | 2. Cache 無界增長 | 穩定性、效能 | 中 | ✅ 2025-12-27 |
| 🔴 Critical | 3. 錯誤靜默失敗 | 用戶體驗 | 小 | ✅ 2025-12-27 |
| 🔴 Critical | 4. Callback 模式不一致 | 可維護性 | 大 | ⬜ |
| ⚠️ Important | 5. 測試覆蓋不完整 | 品質保證 | 大 | ⬜ |
| ⚠️ Important | 6. UI 邏輯混入 | 關注點分離 | 中 | ⬜ |
| ⚠️ Important | 7. 常數重複定義 | 可維護性 | 小 | ✅ 2025-12-27 |
| ⚠️ Important | 8. MCP Timeout | 穩定性 | 中 | ⬜ |
| 💡 Nice-to-have | 9. Async 優化 | 效能 | 小 | ⬜ |
| 💡 Nice-to-have | 10. 程式碼品質 | 可讀性 | 小 | ⬜ |

---

## 🎯 建議實施順序

### Phase 1: 快速修復（1-2 天）
- [x] Issue #7: 常數重複定義 ✅ 2025-12-27
- [x] Issue #1: URL 載入抽取 ✅ 2025-12-27
- [x] Issue #2: Cache 重構（TTL + 淘汰策略）✅ 2025-12-27
- [x] Issue #3: 錯誤處理（建立統一裝飾器）✅ 2025-12-27
- [ ] Issue #9: 移除未使用代碼

### Phase 2: 核心架構（1 週）
- [ ] Issue #6: Presentation layer 抽取

### Phase 3: 長期優化（2-3 週）
- [ ] Issue #4: Callback 模式統一
- [ ] Issue #5: 補充測試覆蓋
- [ ] Issue #8: MCP 連線池

### Phase 4: 精進（持續）
- [ ] Issue #10: 程式碼品質提升
- [ ] 效能監控與優化
- [ ] 文件補充

---

## 📝 備註

- 此文件基於 2025-12-27 的架構分析
- 優先級可依實際需求調整
- 每個 issue 實作前應先撰寫測試
- 遵循專案的 linting、type checking 標準

---

## 📋 變更紀錄

### 2025-12-27: Phase 1 部分完成

#### ✅ Issue #1: URL 載入重複代碼抽取

**問題**：`summary.py`、`translate.py`、`format.py` 重複了相同的 URL 解析和載入邏輯。

**實作內容**：
1. 在 `src/bot/callbacks/utils.py` 新增 `get_processed_message_text()` helper 函數
   - 統一處理訊息文字提取、URL 解析、URL 載入
   - 支援 `require_url` 參數（summary 必須有 URL，translate/format 可選）
   - 返回 `(text, error)` tuple，清楚區分成功與失敗

2. 重構三個 callback：
   - `src/bot/callbacks/summary.py:14-27` - 從 27 行減少到 14 行
   - `src/bot/callbacks/translate.py:17-33` - 簡化 URL 處理邏輯
   - `src/bot/callbacks/format.py:12-31` - 統一錯誤處理

3. 測試覆蓋：
   - 新增 `tests/callbacks/test_utils.py::TestGetProcessedMessageText` (6 個測試)
   - 更新現有測試：`test_summary.py`, `test_format.py`, `test_translate.py`

**影響**：
- ✅ 減少重複代碼 ~30 行
- ✅ 統一錯誤處理模式
- ✅ 提升可維護性
- ✅ 所有測試通過 (39 個測試)

---

#### ✅ Issue #2: Cache TTL 設定防止無界增長

**問題**：
1. Cache 無 TTL，永久保留對話記錄，導致記憶體無限增長
2. 沒有自動過期機制

**實作內容**：
1. 在 `src/bot/constants.py` 新增 `CACHE_TTL_SECONDS = 604800` (1 週)

2. 修改 `src/bot/callbacks/agent.py` cache 策略：
   - **Cache TTL**：所有 `cache.set()` 加入 `ttl=CACHE_TTL_SECONDS`
   - **保留原有架構**：維持 `bot:{message_id}:{chat_id}` key 格式，支援 thread-based 對話

3. 測試覆蓋：
   - 新增 `test_make_cache_key_message_based()` - 驗證 key 格式
   - 新增 `test_cache_ttl_is_set()` - 驗證 TTL 參數
   - 新增 `test_cache_persists_in_reply_thread()` - 驗證 reply thread 中的對話持續性

**影響**：
- ✅ Cache 自動過期（1 週），防止無限增長
- ✅ 維持 thread-based 對話模式（不同主題使用不同 threads）
- ✅ 回覆訊息時自動載入該 thread 的對話歷史
- ✅ 所有測試通過 (26 個測試)

**設計考量**：
- 使用 message-based key 而非 chat-based key，允許在同一 chat 中進行多個獨立的對話串
- 用戶可以透過回覆不同的訊息來切換不同的討論主題
- 1 週的 TTL 提供充足的時間繼續長期討論，同時避免記憶體無限增長

---

#### ✅ Issue #7: 常數重複定義

**問題**：`MAX_LENGTH = 1_000` 在三個檔案中重複定義。

**實作內容**：
1. 建立 `src/bot/constants.py`
2. 定義 `MAX_MESSAGE_LENGTH: Final[int] = 1_000`
3. 重構：`translate.py`, `format.py`, `file_notes.py` 導入常數

**影響**：
- ✅ 集中管理常數
- ✅ 未來修改只需一處
- ✅ 所有測試通過

---

### 📊 統計資訊

**改動檔案**：
- 新增：`src/bot/constants.py` (11 行)
- 修改：8 個檔案
  - `src/bot/callbacks/utils.py` (+45 行)
  - `src/bot/callbacks/agent.py` (~15 行修改)
  - `src/bot/callbacks/summary.py` (-13 行)
  - `src/bot/callbacks/translate.py` (-5 行)
  - `src/bot/callbacks/format.py` (-5 行)
  - `src/bot/callbacks/file_notes.py` (-3 行)
- 測試更新：5 個測試檔案 (+95 行測試)

**測試結果**：
- ✅ Lint: 通過
- ✅ Type check: 通過
- ✅ Tests: 65 個測試全部通過
  - test_utils.py: 23 個測試
  - test_agent.py: 26 個測試
  - test_summary.py: 5 個測試
  - test_format.py: 5 個測試
  - test_translate.py: 6 個測試

**淨效果**：
- 減少重複代碼：~50 行
- 新增測試：~95 行
- 改善可維護性與穩定性

---

#### ✅ Issue #3: 統一錯誤處理機制

**問題**：多處捕捉例外後只記錄 log，用戶不知道發生錯誤。

**實作內容**：
1. 在 `src/bot/callbacks/utils.py` 新增 `safe_callback` 裝飾器
   - 統一處理所有 callback 的例外
   - 通知用戶發生錯誤（友善的繁體中文訊息）
   - 記錄完整錯誤訊息供除錯
   - 重新拋出例外讓全域錯誤處理器可以處理
   - 支援函數和類別方法兩種使用方式

2. 應用裝飾器到所有 callbacks：
   - `src/bot/callbacks/ticker.py` - 股票查詢
   - `src/bot/callbacks/summary.py` - 摘要
   - `src/bot/callbacks/format.py` - 格式化
   - `src/bot/callbacks/translate.py` - 翻譯
   - `src/bot/callbacks/file_notes.py` - 檔案處理
   - `src/bot/callbacks/agent.py` - Agent 對話

3. 改善 ticker.py 的錯誤處理：
   - 當無法查詢到股票資訊時，通知用戶（不再靜默失敗）
   - 改善錯誤訊息的記錄格式

4. 測試覆蓋：
   - 新增 `tests/callbacks/test_utils.py::TestSafeCallback` (4 個測試)
   - 更新現有測試以配合新的錯誤處理行為 (13 個測試檔案)

**影響**：
- ✅ 所有 callback 錯誤都會通知用戶
- ✅ 統一的錯誤訊息格式（繁體中文）
- ✅ 保留完整錯誤記錄供除錯
- ✅ 全域錯誤處理器仍可接收例外
- ✅ 所有測試通過 (223 個測試)

**錯誤訊息範例**：
```
抱歉，處理您的請求時發生錯誤，請稍後再試。
如果問題持續發生，請聯絡管理員。
```

**設計考量**：
- 使用裝飾器模式，最小化程式碼侵入性
- 同時支援函數和類別方法（透過 `hasattr` 檢測）
- 錯誤訊息回覆失敗時不會造成二次錯誤（catch-all 處理）
- 維持例外鏈，讓全域處理器（ErrorCallback）仍可收到通知

---
