from __future__ import annotations

import markdown2
from pydantic import BaseModel
from pydantic import Field

from ..core.prompting import PromptSpec
from ..lazy import lazy_run
from ..presentation import MessageResponse
from ..utils import async_create_page
from .instructions import BASE_INSTRUCTIONS

SUMMARY_PROMPT = PromptSpec(
    id="summary",
    version=1,
    name="summarize",
    input_template="""
請以台灣正體中文為下述內容生成：

在處理輸入內容時，請依循下列執行步驟：

1. 開始前，先產生包含 3-7 點概念性事項的精簡清單（Checklist），簡述你將執行的核心步驟。
2. 依下列要求輸出：

- **推理過程**：條列說明推導出摘要、見解的核心邏輯與步驟。
- **摘要**：對內容進行總結，控制在 200 字以內。
- **見解**：以 Markdown 項目符號（-）列出內容中的主要重點與關鍵啟示，建議 3~5 點，並控制在 200 字內。
- **Hashtags**：提供至少三個與主題相關的英文 Hashtags，前方加上「Hashtags:」，並以單一空格分隔
  （例如 #Taiwan #Stock #DeepLearning）。

# 步驟
1. 保留核心訊息，確保每條重點表達清楚且準確，避免加入任何虛構或未經證實的資訊。適度保留細節，避免過度簡潔。
2. 若發現相似或重複的資訊，請合併為一個重點，以保持內容連貫且流暢。
3. 使用符合台灣用語習慣的表達方式，排除不必要的細節，以提升可讀性。
4. 翻譯摘要、見解成繁體中文，並確保用詞皆為台灣習慣。

注意事項：
- 推理過程必須使用條列格式，建議以數字序號標示。
- 見解使用 Markdown 項目符號（-）列點。
- Hashtags 前需加上「Hashtags:」字樣，並以一連空格分隔各 hashtag。
- 各段落建議單段落 200 字為上限，避免過度冗長。

輸入：
{text}
""",
)


class ThoughtStep(BaseModel):
    context: str = Field(..., description="此步驟考慮的具體情境或條件")
    reasoning: str = Field(..., description="此步驟推理過程的解釋")
    conclusion: str = Field(..., description="此步驟得出的中間結論")

    def __str__(self) -> str:
        return "\n\n".join(
            [
                f"  • <b>情境</b>: {self.context}",
                f"  • <b>推理</b>: {self.reasoning}",
                f"  • <b>結論</b>: {self.conclusion}",
            ]
        )


class ChainOfThought(BaseModel):
    steps: list[ThoughtStep] = Field(..., description="通往最終結論的一系列推理步驟")
    final_conclusion: str = Field(..., description="所有推理步驟後的最終結論")

    def __str__(self) -> str:
        steps = "\n\n".join([f"🔍 <b>步驟 {i + 1}</b>\n\n{step}" for i, step in enumerate(self.steps)])
        return "\n\n".join(
            [
                "🧠 <b>推理過程</b>",
                steps,
                "🎯 <b>最終結論</b>",
                self.final_conclusion,
            ]
        )


class Summary(BaseModel):
    chain_of_thought: ChainOfThought = Field(
        ...,
        description=("通往摘要、見解的推理過程，翻譯成台灣繁體中文。提供一系列推理步驟，說明如何得出摘要、見解。"),
    )
    summary_text: str = Field(
        ...,
        description="對文本的總結，翻譯成台灣繁體中文。保留核心訊息，確保每條重點表達清晰且準確，避免加入任何虛構或未經證實的資訊。",
    )
    insights: list[str] = Field(
        ..., description="從文本中提取的見解，翻譯成台灣繁體中文。使用項目符號列出內容中的主要重點和重要啟示。"
    )
    hashtags: list[str] = Field(
        ...,
        description="與文本相關的 Hashtags",
    )

    async def to_message_response(self) -> MessageResponse:
        """Convert summary to a MessageResponse for sending.

        Creates a Telegraph page for the chain of thought and formats
        the summary, insights, and hashtags into a message.

        Returns:
            MessageResponse ready to be sent to Telegram
        """
        insights = "\n".join([f"  • {insight.strip()}" for insight in self.insights])
        hashtags = " ".join(self.hashtags)

        # Create Telegraph page asynchronously
        url = await async_create_page(
            title="推理過程",
            html_content=markdown2.markdown(str(self.chain_of_thought)),
        )

        content = "\n\n".join(
            [
                "📝 <b>摘要</b>",
                self.summary_text.strip(),
                "💡 <b>見解</b>",
                insights,
                f"🏷️ <b>Hashtags</b>: {hashtags}",
                f"🔗 <a href='{url}'>推理過程</a>",
            ]
        )

        return MessageResponse(content=content, title="摘要")


async def summarize(text: str) -> MessageResponse:
    """Generate a summary of the given text.

    Args:
        text (str): The text to summarize.

    Returns:
        MessageResponse: A formatted response containing the summary, insights, and hashtags.
    """
    summary = await lazy_run(
        input=SUMMARY_PROMPT.render_input(text=text),
        instructions=SUMMARY_PROMPT.render_instructions(BASE_INSTRUCTIONS),
        name=SUMMARY_PROMPT.name or "lazy_run",
        output_type=Summary,
    )
    return await summary.to_message_response()
