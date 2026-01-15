from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

from bot.chains.formatter import Article
from bot.chains.formatter import Section
from bot.chains.formatter import _format
from bot.chains.formatter import format
from bot.presentation import MessageResponse


class TestSection:
    def test_str_representation(self) -> None:
        section = Section(title="標題", content="內容")
        assert str(section) == "標題\n內容"

    def test_model_validation(self) -> None:
        section = Section(title="測試標題", content="測試內容")
        assert section.title == "測試標題"
        assert section.content == "測試內容"


class TestArticle:
    def test_str_representation_single_section(self) -> None:
        article = Article(
            title="文章標題",
            sections=[Section(title="章節1", content="內容1")],
        )

        result = str(article)
        assert "📝 文章標題" in result
        assert "章節1" in result
        assert "內容1" in result

    def test_str_representation_multiple_sections(self) -> None:
        article = Article(
            title="文章標題",
            sections=[
                Section(title="章節1", content="內容1"),
                Section(title="章節2", content="內容2"),
                Section(title="章節3", content="內容3"),
            ],
        )

        result = str(article)
        assert "📝 文章標題" in result
        assert "章節1" in result
        assert "內容1" in result
        assert "章節2" in result
        assert "內容2" in result
        assert "章節3" in result
        assert "內容3" in result

    def test_str_representation_empty_sections(self) -> None:
        article = Article(title="空文章", sections=[])

        result = str(article)
        assert "📝 空文章" in result

    def test_to_message_response(self) -> None:
        article = Article(
            title="測試文章",
            sections=[Section(title="測試章節", content="測試內容")],
        )

        response = article.to_message_response()

        assert isinstance(response, MessageResponse)
        assert response.title == "測試文章"
        assert response.parse_mode is None
        assert "📝 測試文章" in response.content
        assert "測試章節" in response.content
        assert "測試內容" in response.content

    def test_to_message_response_preserves_formatting(self) -> None:
        article = Article(
            title="格式測試",
            sections=[
                Section(title="第一節", content="第一段內容"),
                Section(title="第二節", content="第二段內容"),
            ],
        )

        response = article.to_message_response()
        content = response.content

        # 檢查sections之間有正確的分隔
        assert "第一節\n第一段內容" in content
        assert "第二節\n第二段內容" in content


class TestFormatInternal:
    @pytest.mark.asyncio
    async def test_format_internal_success(self) -> None:
        """測試 _format 函數的基本功能"""
        mock_article = Article(
            title="測試文章",
            sections=[Section(title="測試章節", content="測試內容")],
        )

        with (
            patch("bot.chains.formatter.lazy_run", new_callable=AsyncMock) as mock_lazy_run,
            patch("bot.chains.formatter.trace") as mock_trace,
        ):
            mock_lazy_run.return_value = mock_article
            mock_trace.return_value.__enter__ = lambda *args: None
            mock_trace.return_value.__exit__ = lambda *args: None

            result = await _format("測試文本", lang="台灣正體中文")

            assert result == mock_article
            mock_lazy_run.assert_called_once()
            call_args = mock_lazy_run.call_args
            assert "測試文本" in call_args.args[0]
            assert "台灣正體中文" in call_args.args[0]
            assert call_args.kwargs["output_type"] == Article

    @pytest.mark.asyncio
    async def test_format_internal_with_default_lang(self) -> None:
        """測試 _format 函數使用預設語言"""
        mock_article = Article(
            title="文章",
            sections=[Section(title="章節", content="內容")],
        )

        with (
            patch("bot.chains.formatter.lazy_run", new_callable=AsyncMock) as mock_lazy_run,
            patch("bot.chains.formatter.trace") as mock_trace,
        ):
            mock_lazy_run.return_value = mock_article
            mock_trace.return_value.__enter__ = lambda *args: None
            mock_trace.return_value.__exit__ = lambda *args: None

            result = await _format("測試文本")

            assert result == mock_article
            call_args = mock_lazy_run.call_args
            assert "台灣正體中文" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_format_internal_with_english(self) -> None:
        """測試 _format 函數使用英文"""
        mock_article = Article(
            title="Test Article",
            sections=[Section(title="Test Section", content="Test Content")],
        )

        with (
            patch("bot.chains.formatter.lazy_run", new_callable=AsyncMock) as mock_lazy_run,
            patch("bot.chains.formatter.trace") as mock_trace,
        ):
            mock_lazy_run.return_value = mock_article
            mock_trace.return_value.__enter__ = lambda *args: None
            mock_trace.return_value.__exit__ = lambda *args: None

            result = await _format("Test text", lang="English")

            assert result == mock_article
            call_args = mock_lazy_run.call_args
            assert "English" in call_args.args[0]


class TestFormat:
    @pytest.mark.asyncio
    async def test_format_single_chunk(self) -> None:
        """測試單一 chunk 的情況"""
        short_text = "短文本"
        mock_article = Article(
            title="標題",
            sections=[Section(title="章節", content="內容")],
        )

        with (
            patch("bot.chains.formatter.chunk_on_delimiter") as mock_chunk,
            patch("bot.chains.formatter._format", new_callable=AsyncMock) as mock_format_internal,
        ):
            mock_chunk.return_value = [short_text]
            mock_format_internal.return_value = mock_article

            result = await format(short_text)

            assert result == mock_article
            mock_chunk.assert_called_once_with(short_text)
            # Verify that lang parameter is passed through
            mock_format_internal.assert_called_once_with(short_text, lang="台灣正體中文")

    @pytest.mark.asyncio
    async def test_format_multiple_chunks(self) -> None:
        """測試多個 chunks 的情況"""
        long_text = "很長的文本"
        chunks = ["chunk1", "chunk2", "chunk3"]
        chunk_notes = ["note1", "note2", "note3"]
        mock_article = Article(
            title="標題",
            sections=[
                Section(title="章節1", content="內容1"),
                Section(title="章節2", content="內容2"),
            ],
        )

        with (
            patch("bot.chains.formatter.chunk_on_delimiter") as mock_chunk,
            patch("bot.chains.formatter.create_notes_from_chunk", new_callable=AsyncMock) as mock_create_chunk,
            patch("bot.chains.formatter._format", new_callable=AsyncMock) as mock_format_internal,
        ):
            mock_chunk.return_value = chunks
            mock_create_chunk.side_effect = chunk_notes
            mock_format_internal.return_value = mock_article

            result = await format(long_text)

            assert result == mock_article
            mock_chunk.assert_called_once_with(long_text)
            assert mock_create_chunk.call_count == 3
            # Verify that lang parameter is passed through
            mock_format_internal.assert_called_once_with("\n".join(chunk_notes), lang="台灣正體中文")

    @pytest.mark.asyncio
    async def test_format_with_custom_lang(self) -> None:
        """測試使用自訂語言"""
        text = "Test text"
        mock_article = Article(
            title="Title",
            sections=[Section(title="Section", content="Content")],
        )

        with (
            patch("bot.chains.formatter.chunk_on_delimiter") as mock_chunk,
            patch("bot.chains.formatter._format", new_callable=AsyncMock) as mock_format_internal,
        ):
            mock_chunk.return_value = [text]
            mock_format_internal.return_value = mock_article

            result = await format(text, lang="English")

            assert result == mock_article
            # Verify that custom lang parameter is passed through correctly
            mock_format_internal.assert_called_once_with(text, lang="English")

    @pytest.mark.asyncio
    async def test_format_empty_text(self) -> None:
        """測試空文本的情況"""
        empty_text = ""
        mock_article = Article(title="", sections=[])

        with (
            patch("bot.chains.formatter.chunk_on_delimiter") as mock_chunk,
            patch("bot.chains.formatter._format", new_callable=AsyncMock) as mock_format_internal,
        ):
            mock_chunk.return_value = [empty_text]
            mock_format_internal.return_value = mock_article

            result = await format(empty_text)

            assert result == mock_article

    @pytest.mark.asyncio
    async def test_format_preserves_order(self) -> None:
        """測試多chunk時保持順序"""
        text = "長文本"
        chunks = ["part1", "part2", "part3"]
        notes = ["processed1", "processed2", "processed3"]
        mock_article = Article(
            title="完整文章",
            sections=[Section(title="綜合", content="所有內容")],
        )

        with (
            patch("bot.chains.formatter.chunk_on_delimiter") as mock_chunk,
            patch("bot.chains.formatter.create_notes_from_chunk", new_callable=AsyncMock) as mock_create_chunk,
            patch("bot.chains.formatter._format", new_callable=AsyncMock) as mock_format_internal,
        ):
            mock_chunk.return_value = chunks
            mock_create_chunk.side_effect = notes
            mock_format_internal.return_value = mock_article

            await format(text)

            # 驗證最終傳給 _format 的是按順序組合的
            call_args = mock_format_internal.call_args
            assert call_args.args[0] == "processed1\nprocessed2\nprocessed3"
