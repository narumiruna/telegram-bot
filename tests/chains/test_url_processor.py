from unittest.mock import patch

import pytest

from bot.chains.url_processor import process_url_content
from bot.chains.url_processor import rewrite_url_chunk


class TestUrlProcessor:
    """Test cases for URL content processing."""

    @pytest.mark.asyncio
    @patch("bot.chains.url_processor.lazy_run")
    async def test_rewrite_url_chunk(self, mock_lazy_run):
        """Test rewriting a single URL content chunk."""
        mock_lazy_run.return_value = "這是改寫後的內容"

        result = await rewrite_url_chunk("這是長長的網頁內容...")

        assert result == "這是改寫後的內容"
        mock_lazy_run.assert_called_once()

    @pytest.mark.asyncio
    @patch("bot.chains.url_processor.asyncio.gather")
    @patch("bot.chains.url_processor.lazy_run")
    @patch("bot.chains.url_processor.chunk_on_delimiter")
    async def test_process_url_content_single_chunk(self, mock_chunk, mock_lazy_run, mock_gather):
        """Test processing URL content that fits in a single chunk."""
        # Setup mocks
        mock_chunk.return_value = ["這是單一塊內容"]

        result = await process_url_content("這是完整的 URL 內容")

        # Should return original content unchanged for single chunk
        assert result == "這是完整的 URL 內容"
        mock_chunk.assert_called_once_with("這是完整的 URL 內容", max_length=10_000)
        mock_lazy_run.assert_not_called()
        mock_gather.assert_not_called()

    @pytest.mark.asyncio
    @patch("bot.chains.url_processor.rewrite_url_chunk")
    @patch("bot.chains.url_processor.lazy_run")
    @patch("bot.chains.url_processor.chunk_on_delimiter")
    async def test_process_url_content_multiple_chunks(self, mock_chunk, mock_lazy_run, mock_rewrite):
        """Test processing URL content that requires multiple chunks."""
        # Setup mocks
        mock_chunk.return_value = ["內容塊1", "內容塊2", "內容塊3"]
        mock_rewrite.side_effect = ["改寫1", "改寫2", "改寫3"]
        mock_lazy_run.return_value = "最終整合文章"

        result = await process_url_content("很長的 URL 內容...")

        assert result == "最終整合文章"
        mock_chunk.assert_called_once_with("很長的 URL 內容...", max_length=10_000)

        # Verify rewrite was called for each chunk
        assert mock_rewrite.call_count == 3

        # Verify lazy_run was called once for final integration
        assert mock_lazy_run.call_count == 1

    @pytest.mark.asyncio
    @patch("bot.chains.url_processor.chunk_on_delimiter")
    async def test_process_url_content_empty_content(self, mock_chunk):
        """Test processing empty URL content."""
        mock_chunk.return_value = []

        result = await process_url_content("")

        # Should return original content unchanged
        assert result == ""
        mock_chunk.assert_called_once_with("", max_length=10_000)
