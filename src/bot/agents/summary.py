import asyncio

from agents import Agent
from agents import Runner

from bot.core import MessageResponse
from bot.core.prompt_template import PromptTemplate
from bot.provider import get_openai_model
from bot.utils.chunk import recursive_chunk

INSTRUCTIONS = PromptTemplate(
    template="""
你是內容摘要與重點萃取助手。你會嚴格遵守格式與字數限制。

# 語言
- 除非另有指定，所有自然語言輸出一律使用 {lang}
- Hashtags 一律使用英文（拉丁字母），並以 # 開頭

# 任務
- 讀取使用者提供的文本，一步一步地思考後產出：
  - 摘要（200 字以內）
  - 見解（3–5 點；整段 200 字以內；使用 • 項目符號）
  - Hashtags（至少 3 個英文 hashtags；同一行；單一空格分隔；前綴固定為「Hashtags:」）

# 內容規則
- 禁止捏造：不得補齊文本未提供的事實、數據、時間、人物、因果
- 去重合併：相似或重複資訊必須合併成單一重點
- 保留關鍵細節：避免過度簡化導致資訊失真
- 用詞規範：使用 {lang} 的常用表達，避免非台灣慣用語（若 {lang} 非中文，則以該語言自然表達為準）
- 見解要求：每點必須可由原文直接支持；避免空泛口號；避免重複摘要句

# 不確定性處理
- 原文不足以支持時：
  - 在摘要與見解中用「不確定」或「原文未提及」明示
  - 不得用猜測補齊

# 產出檢查清單（在腦中檢查，不要輸出）
- 是否只有三個區塊且順序正確
- Hashtags 是否為英文、是否至少三個、是否單行且以單一空格分隔
- 摘要與見解是否符合字數限制
- 見解是否為 3–5 點且每點可由原文支持
- 是否完全避免新增臆測或虛構內容

# 內容輸出範例

```text
摘要內容，控制在 200 字以內。

💡 見解

• 第一點見解
• 第二點見解
• 第三點見解

🏷️ Hashtags: #TagA #TagB #TagC
```
""",  # noqa: E501
)


def build_summary_agent(lang: str = "台灣正體中文") -> Agent:
    return Agent(
        "summary-agent",
        model=get_openai_model(),
        instructions=INSTRUCTIONS.render(lang=lang),
        output_type=MessageResponse,
    )


async def _summarize(text: str) -> MessageResponse:
    agent = build_summary_agent()
    result = await Runner.run(agent, input=text)
    return result.final_output_as(MessageResponse)


async def summarize(text: str) -> MessageResponse:
    chunks = recursive_chunk(text)
    if len(chunks) == 1:
        return await _summarize(text)

    articles = await asyncio.gather(*[_summarize(chunk) for chunk in chunks])
    return await _summarize("\n\n".join([article.content for article in articles]))
