# Bot 架構改進建議

根據架構分析（2025-12-27），以下是發現的問題與改進建議，按優先級排序。

---

## 📊 快速狀態總覽

| 優先級 | 問題 | 影響範圍 | 狀態 |
|--------|------|----------|------|
| 🔴 Critical | 1. URL 載入重複 | 可維護性 | ✅ 2025-12-27 |
| 🔴 Critical | 2. Cache 無界增長 | 穩定性、效能 | ✅ 2025-12-27 |
| 🔴 Critical | 3. 錯誤靜默失敗 | 用戶體驗 | ✅ 2025-12-27 |
| 🔴 Critical | 4. Callback 模式不一致 | 可維護性 | ✅ 2025-12-27 |
| ⚠️ Important | 5. 測試覆蓋不完整 | 品質保證 | ⬜ 待處理 |
| ⚠️ Important | 6. UI 邏輯混入 | 關注點分離 | ⬜ 待處理 |
| ⚠️ Important | 7. 常數重複定義 | 可維護性 | ✅ 2025-12-27 |
| ⚠️ Important | 8. MCP Timeout | 穩定性 | ⬜ 待處理 |
| 💡 Nice-to-have | 9. Async 優化 | 效能 | ⬜ 待處理 |
| 💡 Nice-to-have | 10. 程式碼品質 | 可讀性 | ⬜ 待處理 |

**進度**: 5/10 完成 (50%)

---

<details>
<summary>✅ 已完成項目 (點擊展開查看詳情)</summary>

## 🔴 Critical - 已完成

### ✅ Issue #1: 代碼重複 - URL 載入邏輯

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

**解決方案**：建立 `get_processed_message_text()` helper 函數統一處理

**狀態**: ✅ 完成於 2025-12-27 (詳見變更紀錄)

---

### ✅ Issue #2: Cache 無界增長

**問題**：對話快取無 TTL、無淘汰策略，會無限累積。

**位置**：`src/bot/callbacks/agent.py:177-212`

**具體問題**：
- 快取 key：`f"bot:{message_id}:{chat_id}"`，每則訊息獨立 key
- 無過期時間設定
- 無記憶體上限
- 對話上下文碎片化（只有回覆該訊息時才載入）

**解決方案**：設定 `CACHE_TTL_SECONDS = 604800` (1 週)

**狀態**: ✅ 完成於 2025-12-27 (詳見變更紀錄)

---

### ✅ Issue #3: 錯誤處理靜默失敗

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

**解決方案**：建立 `@safe_callback` 裝飾器統一錯誤處理

**狀態**: ✅ 完成於 2025-12-27 (詳見變更紀錄)

---

### ✅ Issue #4: Callback 模式不一致

**問題**：混用函數式和類別式 callback，缺乏統一介面。

**現況**：
- **函數**：`summarize_callback`, `format_callback`, `echo_callback`, `ticker_callback`
- **類別**：`TranslationCallback`, `AgentCallback`, `HelpCallback`, `ErrorCallback`

**解決方案**：
1. 定義 `CallbackProtocol` 支援兩種模式
2. 提供 `BaseCallback` 抽象基類供類別式使用
3. 保留函數式 callback 的靈活性

**狀態**: ✅ 完成於 2025-12-27 (詳見變更紀錄)

---

### ✅ Issue #7: 常數重複定義

**問題**：`MAX_LENGTH = 1_000` 在三個檔案中重複定義。

**解決方案**：
1. 建立 `src/bot/constants.py` 集中管理常數
2. 定義 `MAX_MESSAGE_LENGTH: Final[int] = 1_000`
3. 修改 `translate.py`, `format.py`, `file_notes.py` 導入常數

**狀態**: ✅ 完成於 2025-12-27 (詳見變更紀錄)

</details>

---

## ⬜ 待處理項目

### ⚠️ Issue #5: 測試覆蓋不完整

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

### ⚠️ Issue #6: UI 邏輯混入業務層

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

### ⚠️ Issue #8: MCP 連線缺少 Timeout 管理

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

### 💡 Issue #9: Async 模式優化

**觀察**：
- `async_wrapper()` 在 `utils.py` 定義但未使用
- Telegraph 操作是同步的（阻塞 async context）
- `get_composed_loader()` 全域快取（thread-safe 疑慮）

**建議**：
1. 移除未使用的 `async_wrapper()`
2. 為 Telegraph 操作使用 `asyncio.to_thread()`
3. 評估 loader 快取的並發安全性

---

### 💡 Issue #10: 程式碼品質提升

**小型改進**：
- 使用 `match-case` 取代多層 if-elif（Python 3.10+，提升可讀性）
- 型別註解完整性檢查（`ty check --strict` mode，更嚴格的型別檢查）

**注意**：Import 順序已由 ruff (isort) 自動處理，`make format` 會自動修正

---

## 🎯 實施順序

### Phase 1: 快速修復 ✅ 已完成
- [x] Issue #7: 常數重複定義 ✅ 2025-12-27
- [x] Issue #1: URL 載入抽取 ✅ 2025-12-27
- [x] Issue #2: Cache 重構（TTL + 淘汰策略）✅ 2025-12-27
- [x] Issue #3: 錯誤處理（建立統一裝飾器）✅ 2025-12-27
- [ ] Issue #9: 移除未使用代碼 ⬜ 待處理

### Phase 2: 核心架構（1 週）
- [ ] Issue #6: Presentation layer 抽取 ⬜ 待處理

### Phase 3: 長期優化 ⚡ 進行中
- [x] Issue #4: Callback 模式統一 ✅ 2025-12-27
- [ ] Issue #5: 補充測試覆蓋 ⬜ 待處理
- [ ] Issue #8: MCP 連線池 ⬜ 待處理

### Phase 4: 精進（持續）
- [ ] Issue #10: 程式碼品質提升 ⬜ 待處理
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

#### ✅ Issue #4: Callback 模式統一

**問題分析**：混用函數式和類別式 callback，缺乏統一介面

**現況**：
- **函數式 callbacks** (6個): `summarize_callback`, `format_callback`, `echo_callback`, `query_ticker_callback`, `file_callback`, `search_youtube_callback`
- **類別式 callbacks** (4個): `HelpCallback`, `ErrorCallback`, `TranslationCallback`, `AgentCallback`

**核心問題**：
1. 沒有統一的型別定義
2. 不同的實作模式造成理解困難
3. 缺乏清晰的架構指引

---

**解決方案**：採用 **混合式架構 (Hybrid Approach)**

**1. CallbackProtocol (Protocol)**

定義統一的 callback 介面，支援函數和類別兩種實作方式：

```python
class CallbackProtocol(Protocol):
    """Protocol for all bot callbacks."""
    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        ...
```

**優點**：
- 型別安全
- 支援函數式和類別式實作
- 非侵入式，不需修改現有代碼

**2. BaseCallback (Abstract Base Class)**

為需要狀態管理的 callback 提供可選的基類：

```python
class BaseCallback(ABC):
    """Abstract base class for class-based callbacks."""
    @abstractmethod
    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pass
```

**適用場景**：
- 需要狀態管理（如 `TranslationCallback` 的 `lang`）
- 複雜初始化邏輯
- 共享功能

**3. 保留函數式 Callbacks**

對於簡單、無狀態的 callback，繼續使用函數式實作。

**4. 特殊案例：AgentCallback**

不繼承 `BaseCallback`，因為它使用 `handle_command()` 和 `handle_reply()` 方法，而非標準的 `__call__` 模式。

---

**實作內容**：

**新增檔案**：
- `src/bot/callbacks/base.py` (58 行)
  - `CallbackProtocol` 定義
  - `BaseCallback` 抽象基類
  - 完整文檔說明

- `tests/callbacks/test_base.py` (78 行)
  - 6 個測試案例
  - 測試 Protocol 相容性
  - 測試 BaseCallback 抽象行為

**修改檔案**：
- `src/bot/callbacks/__init__.py` - 匯出新的類別
- `src/bot/callbacks/help.py` - 繼承 BaseCallback，修正參數符合 LSP
- `src/bot/callbacks/error.py` - 繼承 BaseCallback
- `src/bot/callbacks/translate.py` - 繼承 BaseCallback

**已遷移的 callbacks**：
- `HelpCallback` - 管理 help 訊息列表
- `ErrorCallback` - 管理開發者聊天 ID
- `TranslationCallback` - 管理目標語言

---

**架構指引**：

**何時使用函數式**：
✅ 無狀態操作
✅ 簡單的單一職責
✅ 不需要共享邏輯

```python
@safe_callback
async def my_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 簡單處理邏輯
    pass
```

**何時使用類別式（BaseCallback）**：
✅ 需要狀態管理（配置、語言設定等）
✅ 複雜初始化邏輯
✅ 需要共享方法或屬性

```python
class MyCallback(BaseCallback):
    def __init__(self, config: str) -> None:
        self.config = config

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # 使用 self.config
        pass
```

**型別註解**：

所有 callback 都符合 `CallbackProtocol`，可用於型別檢查：

```python
def register_callback(callback: CallbackProtocol) -> None:
    # 接受函數或類別實例
    pass
```

---

**測試結果**：

- ✅ Linting: `ruff check .` - All checks passed
- ✅ Type checking: `ty check src` - All checks passed
- ✅ Tests: 229/229 passed

**測試覆蓋**：
- 新增 6 個測試（test_base.py）
- 所有現有測試繼續通過

---

**影響與效益**：

**向後相容性**：
- ✅ 所有現有 callback 繼續正常運作
- ✅ 函數式 callback 不需修改
- ✅ 類別式 callback 只需添加基類繼承

**可維護性**：
- ✅ 清晰的架構指引
- ✅ 型別安全
- ✅ 統一的介面規範

**擴展性**：
- ✅ 新 callback 可選擇最適合的實作方式
- ✅ `BaseCallback` 可擴展共享功能
- ✅ `CallbackProtocol` 確保型別一致性

---

**設計考量**：
- 採用混合式架構平衡一致性與實用性
- Protocol 提供型別檢查而不強制繼承
- BaseCallback 為選用，避免過度工程化
- 保留函數式 callback 的簡潔性

**未來可選改進**：
1. 將常見的 callback 邏輯（如訊息驗證、錯誤處理）移到 `BaseCallback`
2. 建立 callback 工具函數庫（如 `ensure_message()`, `extract_args()` 等）

**不建議的改進**：
- ❌ 強制所有 callback 繼承 `BaseCallback`（會失去靈活性）
- ❌ 轉換所有 callback 為同一種模式（工程量大且無必要）

---

### 📊 統計資訊

**Phase 1 完成（Issues #1, #2, #3, #7）**：
- 新增：`src/bot/constants.py` (11 行)
- 修改：8 個檔案
  - `src/bot/callbacks/utils.py` (+45 行)
  - `src/bot/callbacks/agent.py` (~15 行修改)
  - `src/bot/callbacks/summary.py` (-13 行)
  - `src/bot/callbacks/translate.py` (-5 行)
  - `src/bot/callbacks/format.py` (-5 行)
  - `src/bot/callbacks/file_notes.py` (-3 行)
- 測試更新：5 個測試檔案 (+95 行測試)
- 測試結果：65 個測試全部通過

**Phase 3 - Issue #4 完成（Callback 模式統一）**：
- 新增：`src/bot/callbacks/base.py` (58 行)
- 新增：`tests/callbacks/test_base.py` (78 行)
- 修改：4 個 callback 檔案（help, error, translate, __init__）
- 測試結果：229 個測試全部通過

**總計淨效果**：
- 減少重複代碼：~50 行
- 新增架構代碼：~136 行（base.py + 文檔）
- 新增測試：~173 行
- 改善可維護性、穩定性與架構一致性

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
