# Issue #4: Callback 模式統一 (Unified Callback Pattern)

## 概述 (Overview)

統一了 bot 中不一致的 callback 模式，建立了清晰的架構指引，同時保持現有代碼的靈活性。

## 問題分析 (Problem Analysis)

**現況**：混用函數式和類別式 callback，缺乏統一介面

- **函數式 callbacks** (6個): `summarize_callback`, `format_callback`, `echo_callback`, `query_ticker_callback`, `file_callback`, `search_youtube_callback`
- **類別式 callbacks** (4個): `HelpCallback`, `ErrorCallback`, `TranslationCallback`, `AgentCallback`

**問題**：
1. 沒有統一的型別定義
2. 不同的實作模式造成理解困難
3. 缺乏清晰的架構指引

## 解決方案 (Solution)

採用 **混合式架構 (Hybrid Approach)**：

### 1. CallbackProtocol (Protocol)

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

### 2. BaseCallback (Abstract Base Class)

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

**已遷移的 callbacks**：
- `HelpCallback` - 管理 help 訊息列表
- `ErrorCallback` - 管理開發者聊天 ID
- `TranslationCallback` - 管理目標語言

### 3. 保留函數式 Callbacks

對於簡單、無狀態的 callback，繼續使用函數式實作：

- `summarize_callback`
- `format_callback`
- `echo_callback`
- `query_ticker_callback`
- `file_callback`
- `search_youtube_callback`

### 4. 特殊案例：AgentCallback

`AgentCallback` **不**繼承 `BaseCallback`，因為它：
- 使用 `handle_command()` 和 `handle_reply()` 方法，而非 `__call__`
- 有特殊的註冊方式（方法直接註冊到 CommandHandler）
- 架構較為獨特，不符合標準 callback 模式

## 實作內容 (Implementation)

### 新增檔案

1. **`src/bot/callbacks/base.py`** (58 行)
   - 定義 `CallbackProtocol`
   - 定義 `BaseCallback`
   - 完整的文檔說明

2. **`tests/callbacks/test_base.py`** (78 行)
   - 6 個測試案例
   - 測試 Protocol 相容性
   - 測試 BaseCallback 抽象類別行為

### 修改檔案

1. **`src/bot/callbacks/__init__.py`**
   - 匯出 `BaseCallback` 和 `CallbackProtocol`

2. **`src/bot/callbacks/help.py`**
   - 繼承 `BaseCallback`
   - 修正參數名稱（`_` → `context`）符合 LSP

3. **`src/bot/callbacks/error.py`**
   - 繼承 `BaseCallback`

4. **`src/bot/callbacks/translate.py`**
   - 繼承 `BaseCallback`

## 架構指引 (Architecture Guidelines)

### 何時使用函數式 Callback

✅ **適合使用函數**：
- 無狀態操作
- 簡單的單一職責
- 不需要共享邏輯

```python
@safe_callback
async def my_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 簡單處理邏輯
    pass
```

### 何時使用類別式 Callback

✅ **適合使用類別（繼承 BaseCallback）**：
- 需要狀態管理（配置、語言設定等）
- 複雜初始化邏輯
- 需要共享方法或屬性

```python
class MyCallback(BaseCallback):
    def __init__(self, config: str) -> None:
        self.config = config

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # 使用 self.config
        pass
```

### 型別註解

所有 callback 都符合 `CallbackProtocol`，可用於型別檢查：

```python
def register_callback(callback: CallbackProtocol) -> None:
    # 接受函數或類別實例
    pass
```

## 測試結果 (Test Results)

### 測試覆蓋

- **新增測試**：6 個測試（test_base.py）
- **總測試數**：229 個測試
- **測試結果**：✅ 全部通過

### 品質檢查

- ✅ Linting: `ruff check .` - All checks passed
- ✅ Type checking: `ty check src` - All checks passed
- ✅ Tests: 229 passed

## 統計資訊 (Statistics)

**新增**：
- 1 個新模組：`src/bot/callbacks/base.py` (58 行)
- 1 個測試檔案：`tests/callbacks/test_base.py` (78 行)

**修改**：
- 4 個 callback 檔案（help, error, translate, __init__）
- 總計約 15 行修改

**淨效果**：
- ✅ 統一 callback 架構
- ✅ 提供清晰的型別定義
- ✅ 保持代碼靈活性
- ✅ 不破壞現有功能
- ✅ 完整的測試覆蓋

## 影響範圍 (Impact)

### 向後相容性

✅ **完全向後相容**：
- 所有現有 callback 繼續正常運作
- 函數式 callback 不需修改
- 類別式 callback 只需添加基類繼承

### 可維護性

✅ **提升可維護性**：
- 清晰的架構指引
- 型別安全
- 統一的介面規範

### 擴展性

✅ **易於擴展**：
- 新 callback 可選擇最適合的實作方式
- `BaseCallback` 可擴展共享功能
- `CallbackProtocol` 確保型別一致性

## 未來改進 (Future Improvements)

### 可選改進項目

1. **共享功能遷移**：將常見的 callback 邏輯（如訊息驗證、錯誤處理）移到 `BaseCallback`
2. **文檔補充**：在 CLAUDE.md 中加入 callback 開發指南
3. **工具函數**：建立 callback 工具函數庫（如 `ensure_message()`, `extract_args()` 等）

### 不建議的改進

❌ **不建議**：
- 強制所有 callback 繼承 `BaseCallback`（會失去靈活性）
- 轉換所有 callback 為同一種模式（函數或類別）（工程量大且無必要）

## 結論 (Conclusion)

Issue #4 已成功完成，採用混合式架構達到以下目標：

1. ✅ **統一性**：通過 `CallbackProtocol` 提供統一介面
2. ✅ **靈活性**：支援函數式和類別式兩種實作
3. ✅ **可維護性**：清晰的架構指引和型別定義
4. ✅ **向後相容**：不破壞現有代碼
5. ✅ **測試覆蓋**：完整的測試確保品質

這個方案平衡了一致性與實用性，為未來的開發提供了清晰的方向。

---

**完成日期**：2025-12-27
**狀態**：✅ 已完成
**測試**：✅ 229/229 通過
**品質**：✅ Lint & Type check 通過
