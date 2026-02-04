from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

from bot.chains.summary import ChainOfThought
from bot.chains.summary import Summary
from bot.chains.summary import ThoughtStep
from bot.chains.summary import summarize
from bot.core.presentation import MessageResponse


class TestThoughtStep:
    def test_str_representation(self) -> None:
        step = ThoughtStep(
            context="測試情境",
            reasoning="測試推理",
            conclusion="測試結論",
        )

        result = str(step)
        assert "• <b>情境</b>: 測試情境" in result
        assert "• <b>推理</b>: 測試推理" in result
        assert "• <b>結論</b>: 測試結論" in result

    def test_model_validation(self) -> None:
        step = ThoughtStep(
            context="情境內容",
            reasoning="推理過程",
            conclusion="得出結論",
        )

        assert step.context == "情境內容"
        assert step.reasoning == "推理過程"
        assert step.conclusion == "得出結論"


class TestChainOfThought:
    def test_str_representation_single_step(self) -> None:
        chain = ChainOfThought(
            steps=[
                ThoughtStep(
                    context="情境1",
                    reasoning="推理1",
                    conclusion="結論1",
                )
            ],
            final_conclusion="最終結論",
        )

        result = str(chain)
        assert "🧠 <b>推理過程</b>" in result
        assert "🔍 <b>步驟 1</b>" in result
        assert "情境1" in result
        assert "推理1" in result
        assert "結論1" in result
        assert "🎯 <b>最終結論</b>" in result
        assert "最終結論" in result

    def test_str_representation_multiple_steps(self) -> None:
        chain = ChainOfThought(
            steps=[
                ThoughtStep(context="情境1", reasoning="推理1", conclusion="結論1"),
                ThoughtStep(context="情境2", reasoning="推理2", conclusion="結論2"),
                ThoughtStep(context="情境3", reasoning="推理3", conclusion="結論3"),
            ],
            final_conclusion="綜合結論",
        )

        result = str(chain)
        assert "步驟 1" in result
        assert "步驟 2" in result
        assert "步驟 3" in result
        assert "情境1" in result
        assert "情境2" in result
        assert "情境3" in result
        assert "綜合結論" in result

    def test_str_representation_empty_steps(self) -> None:
        chain = ChainOfThought(
            steps=[],
            final_conclusion="無步驟的結論",
        )

        result = str(chain)
        assert "🧠 <b>推理過程</b>" in result
        assert "🎯 <b>最終結論</b>" in result
        assert "無步驟的結論" in result


class TestSummarize:
    @pytest.mark.asyncio
    async def test_summarize_success(self) -> None:
        """測試 summarize 函數的基本功能"""
        test_text = "這是要被總結的文本內容"

        mock_summary = Summary(
            chain_of_thought=ChainOfThought(
                steps=[ThoughtStep(context="測試", reasoning="測試", conclusion="測試")],
                final_conclusion="測試結論",
            ),
            summary_text="總結內容",
            insights=["見解1", "見解2"],
            hashtags=["#test1", "#test2"],
        )

        mock_response = MessageResponse(content="測試內容", title="摘要")

        with (
            patch("bot.chains.summary.lazy_run", new_callable=AsyncMock) as mock_lazy_run,
            patch.object(Summary, "to_message_response", new_callable=AsyncMock) as mock_to_response,
        ):
            mock_lazy_run.return_value = mock_summary
            mock_to_response.return_value = mock_response

            result = await summarize(test_text)

            assert result == mock_response
            mock_lazy_run.assert_called_once()
            call_args = mock_lazy_run.call_args
            assert test_text in call_args.kwargs["input"]
            assert call_args.kwargs["output_type"] == Summary
            mock_to_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_uses_prompt_template(self) -> None:
        """測試 summarize 使用正確的提示模板"""
        test_text = "測試文本"

        mock_summary = Summary(
            chain_of_thought=ChainOfThought(steps=[], final_conclusion="結論"),
            summary_text="摘要",
            insights=["見解"],
            hashtags=["#tag"],
        )

        mock_response = MessageResponse(content="內容", title="摘要")

        with (
            patch("bot.chains.summary.lazy_run", new_callable=AsyncMock) as mock_lazy_run,
            patch.object(Summary, "to_message_response", new_callable=AsyncMock) as mock_to_response,
        ):
            mock_lazy_run.return_value = mock_summary
            mock_to_response.return_value = mock_response

            await summarize(test_text)

            call_args = mock_lazy_run.call_args
            prompt = call_args.kwargs["input"]

            # 驗證提示模板包含必要元素
            assert "台灣正體中文" in prompt
            assert "推理過程" in prompt
            assert "摘要" in prompt
            assert "見解" in prompt
            assert "Hashtags" in prompt
            assert test_text in prompt

    @pytest.mark.asyncio
    async def test_summarize_empty_text(self) -> None:
        """測試空文本的處理"""
        empty_text = ""

        mock_summary = Summary(
            chain_of_thought=ChainOfThought(steps=[], final_conclusion=""),
            summary_text="",
            insights=[],
            hashtags=[],
        )

        mock_response = MessageResponse(content="", title="摘要")

        with (
            patch("bot.chains.summary.lazy_run", new_callable=AsyncMock) as mock_lazy_run,
            patch.object(Summary, "to_message_response", new_callable=AsyncMock) as mock_to_response,
        ):
            mock_lazy_run.return_value = mock_summary
            mock_to_response.return_value = mock_response

            result = await summarize(empty_text)

            assert result == mock_response
