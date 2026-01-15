from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

from bot.chains.notes import CausalRelationship
from bot.chains.notes import ResearchReport
from bot.chains.notes import create_notes
from bot.chains.notes import create_notes_from_chunk
from bot.chains.notes import extract_notes


class TestCausalRelationship:
    def test_str_representation(self) -> None:
        relationship = CausalRelationship(cause="高溫", effect="冰融化")
        assert str(relationship) == "高溫 -> 冰融化"

    def test_model_validation(self) -> None:
        relationship = CausalRelationship(cause="原因", effect="結果")
        assert relationship.cause == "原因"
        assert relationship.effect == "結果"


class TestResearchReport:
    def test_str_representation_with_all_fields(self) -> None:
        report = ResearchReport(
            title="研究標題",
            abstract="摘要內容",
            introduction="介紹內容",
            methodology="方法內容",
            highlights=["重點1", "重點2"],
            causal_relationships=[
                CausalRelationship(cause="原因1", effect="結果1"),
                CausalRelationship(cause="原因2", effect="結果2"),
            ],
            conclusion="結論內容",
        )

        result = str(report)
        assert "研究標題" in result
        assert "📝 摘要\n摘要內容" in result
        assert "🔍 介紹\n介紹內容" in result
        assert "⚙️ 方法\n方法內容" in result
        assert "✨ 重點" in result
        assert "- 重點1" in result
        assert "- 重點2" in result
        assert "🔄 因果關係" in result
        assert "- 原因1 -> 結果1" in result
        assert "- 原因2 -> 結果2" in result
        assert "🎯 結論\n結論內容" in result

    def test_str_representation_without_highlights(self) -> None:
        report = ResearchReport(
            title="標題",
            abstract="摘要",
            introduction="介紹",
            methodology="方法",
            highlights=[],
            causal_relationships=[],
            conclusion="結論",
        )

        result = str(report)
        assert "標題" in result
        assert "摘要" in result
        assert "✨ 重點" not in result
        assert "🔄 因果關係" not in result

    def test_str_representation_with_highlights_only(self) -> None:
        report = ResearchReport(
            title="標題",
            abstract="摘要",
            introduction="介紹",
            methodology="方法",
            highlights=["重點1"],
            causal_relationships=[],
            conclusion="結論",
        )

        result = str(report)
        assert "✨ 重點" in result
        assert "- 重點1" in result
        assert "🔄 因果關係" not in result

    def test_str_representation_with_relationships_only(self) -> None:
        report = ResearchReport(
            title="標題",
            abstract="摘要",
            introduction="介紹",
            methodology="方法",
            highlights=[],
            causal_relationships=[CausalRelationship(cause="原因", effect="結果")],
            conclusion="結論",
        )

        result = str(report)
        assert "✨ 重點" not in result
        assert "🔄 因果關係" in result
        assert "- 原因 -> 結果" in result


class TestExtractNotes:
    @pytest.mark.asyncio
    async def test_extract_notes_success(self) -> None:
        mock_report = ResearchReport(
            title="測試標題",
            abstract="測試摘要",
            introduction="測試介紹",
            methodology="測試方法",
            highlights=["測試重點"],
            causal_relationships=[CausalRelationship(cause="測試原因", effect="測試結果")],
            conclusion="測試結論",
        )

        with patch("bot.chains.notes.lazy_run", new_callable=AsyncMock) as mock_lazy_run:
            mock_lazy_run.return_value = mock_report

            result = await extract_notes("測試文本", lang="台灣正體中文")

            assert result == mock_report
            mock_lazy_run.assert_called_once()
            call_args = mock_lazy_run.call_args
            assert "測試文本" in call_args.kwargs["input"]
            assert "台灣正體中文" in call_args.kwargs["input"]
            assert call_args.kwargs["output_type"] == ResearchReport

    @pytest.mark.asyncio
    async def test_extract_notes_with_default_lang(self) -> None:
        mock_report = ResearchReport(
            title="標題",
            abstract="摘要",
            introduction="介紹",
            methodology="方法",
            highlights=[],
            causal_relationships=[],
            conclusion="結論",
        )

        with patch("bot.chains.notes.lazy_run", new_callable=AsyncMock) as mock_lazy_run:
            mock_lazy_run.return_value = mock_report

            result = await extract_notes("測試文本")

            assert result == mock_report
            call_args = mock_lazy_run.call_args
            assert "台灣正體中文" in call_args.kwargs["input"]


class TestCreateNotesFromChunk:
    @pytest.mark.asyncio
    async def test_create_notes_from_chunk_success(self) -> None:
        expected_notes = "這是生成的筆記內容"

        with patch("bot.chains.notes.lazy_run", new_callable=AsyncMock) as mock_lazy_run:
            mock_lazy_run.return_value = expected_notes

            result = await create_notes_from_chunk("測試文本塊")

            assert result == expected_notes
            mock_lazy_run.assert_called_once()
            call_args = mock_lazy_run.call_args
            assert "測試文本塊" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_create_notes_from_chunk_with_special_characters(self) -> None:
        text_with_special_chars = "測試\n換行\t縮排"
        expected_notes = "處理後的筆記"

        with patch("bot.chains.notes.lazy_run", new_callable=AsyncMock) as mock_lazy_run:
            mock_lazy_run.return_value = expected_notes

            result = await create_notes_from_chunk(text_with_special_chars)

            assert result == expected_notes


class TestCreateNotes:
    @pytest.mark.asyncio
    async def test_create_notes_single_chunk(self) -> None:
        """測試單一 chunk 的情況，應該直接調用 extract_notes"""
        short_text = "短文本"
        mock_report = ResearchReport(
            title="標題",
            abstract="摘要",
            introduction="介紹",
            methodology="方法",
            highlights=[],
            causal_relationships=[],
            conclusion="結論",
        )

        with (
            patch("bot.chains.notes.chunk_on_delimiter") as mock_chunk,
            patch("bot.chains.notes.extract_notes", new_callable=AsyncMock) as mock_extract,
        ):
            mock_chunk.return_value = [short_text]
            mock_extract.return_value = mock_report

            result = await create_notes(short_text)

            assert result == mock_report
            mock_chunk.assert_called_once_with(short_text)
            mock_extract.assert_called_once_with(short_text)

    @pytest.mark.asyncio
    async def test_create_notes_multiple_chunks(self) -> None:
        """測試多個 chunks 的情況，應該先處理每個 chunk 再整合"""
        long_text = "很長的文本"
        chunks = ["chunk1", "chunk2", "chunk3"]
        chunk_notes = ["note1", "note2", "note3"]
        mock_report = ResearchReport(
            title="標題",
            abstract="摘要",
            introduction="介紹",
            methodology="方法",
            highlights=["重點"],
            causal_relationships=[],
            conclusion="結論",
        )

        with (
            patch("bot.chains.notes.chunk_on_delimiter") as mock_chunk,
            patch("bot.chains.notes.create_notes_from_chunk", new_callable=AsyncMock) as mock_create_chunk,
            patch("bot.chains.notes.extract_notes", new_callable=AsyncMock) as mock_extract,
        ):
            mock_chunk.return_value = chunks
            mock_create_chunk.side_effect = chunk_notes
            mock_extract.return_value = mock_report

            result = await create_notes(long_text)

            assert result == mock_report
            mock_chunk.assert_called_once_with(long_text)
            assert mock_create_chunk.call_count == 3
            mock_extract.assert_called_once_with("\n".join(chunk_notes))

    @pytest.mark.asyncio
    async def test_create_notes_empty_text(self) -> None:
        """測試空文本的情況"""
        empty_text = ""
        mock_report = ResearchReport(
            title="",
            abstract="",
            introduction="",
            methodology="",
            highlights=[],
            causal_relationships=[],
            conclusion="",
        )

        with (
            patch("bot.chains.notes.chunk_on_delimiter") as mock_chunk,
            patch("bot.chains.notes.extract_notes", new_callable=AsyncMock) as mock_extract,
        ):
            mock_chunk.return_value = [empty_text]
            mock_extract.return_value = mock_report

            result = await create_notes(empty_text)

            assert result == mock_report
