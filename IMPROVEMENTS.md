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
- 統一 import 順序（stdlib → 3rd party → local）
- 使用 `match-case` 取代多層 if-elif（Python 3.10+）
- 型別註解完整性檢查（`--strict` mode）

---

## 📊 優先級排序總結

| 優先級 | 問題 | 影響範圍 | 工作量 | 狀態 |
|--------|------|----------|--------|------|
| 🔴 Critical | 1. URL 載入重複 | 可維護性 | 中 | ⬜ |
| 🔴 Critical | 2. Cache 無界增長 | 穩定性、效能 | 中 | ⬜ |
| 🔴 Critical | 3. 錯誤靜默失敗 | 用戶體驗 | 小 | ⬜ |
| 🔴 Critical | 4. Callback 模式不一致 | 可維護性 | 大 | ⬜ |
| ⚠️ Important | 5. 測試覆蓋不完整 | 品質保證 | 大 | ⬜ |
| ⚠️ Important | 6. UI 邏輯混入 | 關注點分離 | 中 | ⬜ |
| ⚠️ Important | 7. 常數重複定義 | 可維護性 | 小 | ✅ |
| ⚠️ Important | 8. MCP Timeout | 穩定性 | 中 | ⬜ |
| 💡 Nice-to-have | 9. Async 優化 | 效能 | 小 | ⬜ |
| 💡 Nice-to-have | 10. 程式碼品質 | 可讀性 | 小 | ⬜ |

---

## 🎯 建議實施順序

### Phase 1: 快速修復（1-2 天）
- [x] Issue #7: 常數重複定義
- [ ] Issue #3: 錯誤處理（建立統一裝飾器）
- [ ] Issue #9: 移除未使用代碼

### Phase 2: 核心架構（1 週）
- [ ] Issue #1: URL 載入抽取
- [ ] Issue #2: Cache 重構（TTL + 淘汰策略）
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
