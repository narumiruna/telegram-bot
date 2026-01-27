"""
Comprehensive tests for file upload processing callback.

Tests file upload handling, PDF/HTML content extraction, text formatting,
Telegraph page creation, and various error scenarios.
"""

from pathlib import Path
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from aiogram.types import Document
from aiogram.types import File
from aiogram.types import Message
from aiogram.types import Update

from bot.callbacks.file_notes import file_callback
from bot.chains.formatter import Article
from bot.chains.formatter import Section
from bot.constants import MAX_MESSAGE_LENGTH


class TestFileCallback:
    """Test the file_callback function."""

    @pytest.fixture
    def mock_update(self):
        """Create a mock Telegram update with file upload."""
        update = Mock(spec=Update)
        message = Mock(spec=Message)
        document = Mock(spec=Document)

        document.file_id = "test_file_id"
        message.document = document
        message.answer = AsyncMock()
        update.message = message

        return update

    @pytest.fixture
    def mock_context(self):
        """Create a mock Telegram context."""
        context = Mock()
        bot = Mock()
        file_obj = Mock(spec=File)

        file_obj.download_to_drive = AsyncMock()
        bot.get_file = AsyncMock(return_value=file_obj)
        context.bot = bot

        return context

    @pytest.fixture
    def sample_article(self):
        """Create a sample Article object for testing."""
        return Article(
            title="Test Document",
            sections=[
                Section(title="🔍 Section 1", content="This is the first section content."),
                Section(title="📊 Section 2", content="This is the second section content."),
            ],
        )

    @pytest.mark.asyncio
    async def test_file_callback_no_message(self, mock_context):
        """Test file_callback when update has no message."""
        update = Mock(spec=Update)
        update.message = None

        # Should return early without processing
        await file_callback(update, mock_context)

        # Verify no bot interactions
        mock_context.bot.get_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_file_callback_no_document(self, mock_context):
        """Test file_callback when message has no document."""
        update = Mock(spec=Update)
        message = Mock(spec=Message)
        message.document = None
        update.message = message

        # Should return early without processing
        await file_callback(update, mock_context)

        # Verify no bot interactions
        mock_context.bot.get_file.assert_not_called()

    @pytest.mark.asyncio
    @patch("bot.callbacks.file_notes.read_pdf_content")
    @patch("bot.callbacks.file_notes.chains.format")
    @patch("bot.callbacks.file_notes.os.remove")
    async def test_file_callback_pdf_success_short_content(
        self, mock_remove, mock_format, mock_read_pdf, mock_update, mock_context, sample_article
    ):
        """Test successful PDF processing with short content."""
        # Setup mocks
        test_file_path = Path("/tmp/test.pdf")
        mock_context.bot.get_file.return_value.download_to_drive.return_value = test_file_path
        mock_read_pdf.return_value = "Sample PDF content for testing"
        mock_format.return_value = sample_article

        # Execute
        await file_callback(mock_update, mock_context)

        # Verify file download and processing
        mock_context.bot.get_file.assert_called_once_with("test_file_id")
        mock_context.bot.get_file.return_value.download_to_drive.assert_called_once()
        mock_read_pdf.assert_called_once_with(test_file_path)
        mock_format.assert_called_once_with("Sample PDF content for testing")

        # Verify file cleanup
        mock_remove.assert_called_once_with(test_file_path)

        # Verify response (MessageResponse.send() calls message.answer with parse_mode=None)
        mock_update.message.answer.assert_called_once()

    @pytest.mark.asyncio
    @patch("bot.callbacks.file_notes.read_html_content")
    @patch("bot.callbacks.file_notes.chains.format")
    @patch("bot.callbacks.file_notes.os.remove")
    async def test_file_callback_html_success_short_content(
        self, mock_remove, mock_format, mock_read_html, mock_update, mock_context, sample_article
    ):
        """Test successful HTML processing with short content."""
        # Setup mocks
        test_file_path = Path("/tmp/test.html")
        mock_context.bot.get_file.return_value.download_to_drive.return_value = test_file_path
        mock_read_html.return_value = "Sample HTML content for testing"
        mock_format.return_value = sample_article

        # Execute
        await file_callback(mock_update, mock_context)

        # Verify file download and processing
        mock_context.bot.get_file.assert_called_once_with("test_file_id")
        mock_read_html.assert_called_once_with(test_file_path)
        mock_format.assert_called_once_with("Sample HTML content for testing")

        # Verify file cleanup
        mock_remove.assert_called_once_with(test_file_path)

        # Verify response
        mock_update.message.answer.assert_called_once()

    @pytest.mark.asyncio
    @patch("bot.callbacks.file_notes.read_pdf_content")
    @patch("bot.callbacks.file_notes.chains.format")
    @patch("bot.presentation.async_create_page")
    @patch("bot.callbacks.file_notes.os.remove")
    async def test_file_callback_pdf_success_long_content(
        self, mock_remove, mock_async_create_page, mock_format, mock_read_pdf, mock_update, mock_context
    ):
        """Test successful PDF processing with long content that requires Telegraph page."""
        # Setup mocks for long content
        long_content_sections = [
            Section(title="🔍 Long Section", content="A" * 500),
            Section(title="📊 Another Long Section", content="B" * 600),
        ]
        long_article = Article(title="Long Document", sections=long_content_sections)

        test_file_path = Path("/tmp/test.pdf")
        mock_context.bot.get_file.return_value.download_to_drive.return_value = test_file_path
        mock_read_pdf.return_value = "Long PDF content for testing"
        mock_format.return_value = long_article
        mock_async_create_page.return_value = "https://telegra.ph/test-page-123"

        # Execute
        await file_callback(mock_update, mock_context)

        # Verify processing
        mock_read_pdf.assert_called_once_with(test_file_path)
        mock_format.assert_called_once_with("Long PDF content for testing")

        # Verify Telegraph page creation for long content (via MessageResponse.send())
        mock_async_create_page.assert_called_once()

        # Verify response with Telegraph URL
        mock_update.message.answer.assert_called_once_with("https://telegra.ph/test-page-123")

        # Verify cleanup
        mock_remove.assert_called_once_with(test_file_path)

    @pytest.mark.asyncio
    @patch("bot.callbacks.file_notes.read_pdf_content")
    @patch("bot.callbacks.file_notes.os.remove")
    async def test_file_callback_pdf_empty_content(self, mock_remove, mock_read_pdf, mock_update, mock_context):
        """Test PDF processing when extracted content is empty."""
        # Setup mocks
        test_file_path = Path("/tmp/test.pdf")
        mock_context.bot.get_file.return_value.download_to_drive.return_value = test_file_path
        mock_read_pdf.return_value = ""  # Empty content

        # Execute
        await file_callback(mock_update, mock_context)

        # Verify file processing
        mock_read_pdf.assert_called_once_with(test_file_path)

        # Verify file cleanup still happens
        mock_remove.assert_called_once_with(test_file_path)

        # Verify no reply is sent for empty content
        mock_update.message.answer.assert_not_called()

    @pytest.mark.asyncio
    @patch("bot.callbacks.file_notes.read_html_content")
    @patch("bot.callbacks.file_notes.chains.format")
    @patch("bot.callbacks.file_notes.os.remove")
    async def test_file_callback_html_whitespace_only_content(
        self, mock_remove, mock_format, mock_read_html, mock_update, mock_context, sample_article
    ):
        """Test HTML processing when extracted content is whitespace only."""
        # Setup mocks
        test_file_path = Path("/tmp/test.html")
        mock_context.bot.get_file.return_value.download_to_drive.return_value = test_file_path
        mock_read_html.return_value = "   \n\t  \n  "  # Whitespace only
        mock_format.return_value = sample_article

        # Execute
        await file_callback(mock_update, mock_context)

        # Verify file processing
        mock_read_html.assert_called_once_with(test_file_path)

        # Verify file cleanup
        mock_remove.assert_called_once_with(test_file_path)

        # Whitespace-only content is truthy in Python, so it gets processed
        mock_format.assert_called_once_with("   \n\t  \n  ")
        mock_update.message.answer.assert_called_once()

    @pytest.mark.asyncio
    @patch("bot.callbacks.file_notes.os.remove")
    async def test_file_callback_unsupported_file_type(self, mock_remove, mock_update, mock_context):
        """Test file callback with unsupported file type."""
        # Setup mocks
        test_file_path = Path("/tmp/test.txt")  # Unsupported type
        mock_context.bot.get_file.return_value.download_to_drive.return_value = test_file_path

        # Execute
        await file_callback(mock_update, mock_context)

        # Verify file download happened
        mock_context.bot.get_file.assert_called_once_with("test_file_id")

        # Verify file cleanup
        mock_remove.assert_called_once_with(test_file_path)

        # Verify no reply for unsupported file type
        mock_update.message.answer.assert_not_called()

    @pytest.mark.asyncio
    @patch("bot.callbacks.file_notes.read_pdf_content")
    @patch("bot.callbacks.file_notes.os.remove")
    async def test_file_callback_pdf_read_error(self, mock_remove, mock_read_pdf, mock_update, mock_context):
        """Test PDF processing when read_pdf_content raises an error."""
        # Setup mocks
        test_file_path = Path("/tmp/test.pdf")
        mock_context.bot.get_file.return_value.download_to_drive.return_value = test_file_path
        mock_read_pdf.side_effect = Exception("PDF reading failed")

        # Execute - should raise exception and notify user
        with pytest.raises(Exception, match="PDF reading failed"):
            await file_callback(mock_update, mock_context)

        # Verify file processing was attempted
        mock_read_pdf.assert_called_once_with(test_file_path)

        # File cleanup should still happen even if content reading fails
        mock_remove.assert_called_once_with(test_file_path)

        # Verify user was notified of error
        mock_update.message.answer.assert_called_once()
        call_args = mock_update.message.answer.call_args[0][0]
        assert "抱歉" in call_args
        assert "錯誤" in call_args

    @pytest.mark.asyncio
    @patch("bot.callbacks.file_notes.read_pdf_content")
    @patch("bot.callbacks.file_notes.chains.format")
    @patch("bot.presentation.async_create_page")
    @patch("bot.callbacks.file_notes.os.remove")
    async def test_file_callback_telegraph_creation_error(
        self, mock_remove, mock_async_create_page, mock_format, mock_read_pdf, mock_update, mock_context
    ):
        """Test when Telegraph page creation fails."""
        # Setup mocks for long content
        long_article = Article(
            title="Long Document", sections=[Section(title="🔍 Long Section", content="A" * MAX_MESSAGE_LENGTH)]
        )

        test_file_path = Path("/tmp/test.pdf")
        mock_context.bot.get_file.return_value.download_to_drive.return_value = test_file_path
        mock_read_pdf.return_value = "Long PDF content"
        mock_format.return_value = long_article
        mock_async_create_page.side_effect = Exception("Telegraph creation failed")

        # Execute - should raise exception and notify user
        with pytest.raises(Exception, match="Telegraph creation failed"):
            await file_callback(mock_update, mock_context)

        # Verify processing
        mock_read_pdf.assert_called_once_with(test_file_path)
        mock_format.assert_called_once_with("Long PDF content")
        mock_async_create_page.assert_called_once()

        # Verify file cleanup happens before Telegraph creation
        mock_remove.assert_called_once_with(test_file_path)

        # Verify user was notified of error
        mock_update.message.answer.assert_called_once()
        call_args = mock_update.message.answer.call_args[0][0]
        assert "抱歉" in call_args
        assert "錯誤" in call_args


class TestMaxLengthConstant:
    """Test the MAX_MESSAGE_LENGTH constant usage."""

    def test_max_length_value(self):
        """Test that MAX_MESSAGE_LENGTH has expected value."""
        assert MAX_MESSAGE_LENGTH == 1_000


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    @pytest.mark.asyncio
    @patch("bot.callbacks.file_notes.read_pdf_content")
    @patch("bot.callbacks.file_notes.chains.format")
    @patch("bot.callbacks.file_notes.os.remove")
    async def test_complete_pdf_workflow(self, mock_remove, mock_format, mock_read_pdf):
        """Test complete PDF processing workflow end-to-end."""
        # Setup complete mock chain
        update = Mock(spec=Update)
        message = Mock(spec=Message)
        document = Mock(spec=Document)
        context = Mock()
        bot = Mock()
        file_obj = Mock(spec=File)

        # Configure mocks
        document.file_id = "pdf_file_123"
        message.document = document
        message.answer = AsyncMock()
        update.message = message

        test_file_path = Path("/tmp/uploaded.pdf")
        file_obj.download_to_drive = AsyncMock(return_value=test_file_path)
        bot.get_file = AsyncMock(return_value=file_obj)
        context.bot = bot

        mock_read_pdf.return_value = "Extracted PDF text content"
        mock_format.return_value = Article(
            title="Processed Document", sections=[Section(title="📄 Content", content="Formatted content")]
        )

        # Execute workflow
        await file_callback(update, context)

        # Verify complete chain
        bot.get_file.assert_called_once_with("pdf_file_123")
        file_obj.download_to_drive.assert_called_once()
        mock_read_pdf.assert_called_once_with(test_file_path)
        mock_format.assert_called_once_with("Extracted PDF text content")
        mock_remove.assert_called_once_with(test_file_path)

        # Verify response (MessageResponse.send() is called)
        message.answer.assert_called_once()

    @pytest.mark.asyncio
    @patch("bot.callbacks.file_notes.read_html_content")
    @patch("bot.callbacks.file_notes.chains.format")
    @patch("bot.presentation.async_create_page")
    @patch("bot.callbacks.file_notes.os.remove")
    async def test_complete_html_workflow_with_telegraph(
        self, mock_remove, mock_async_create_page, mock_format, mock_read_html
    ):
        """Test complete HTML processing workflow with Telegraph page creation."""
        # Setup mocks
        update = Mock(spec=Update)
        message = Mock(spec=Message)
        document = Mock(spec=Document)
        context = Mock()
        bot = Mock()
        file_obj = Mock(spec=File)

        document.file_id = "html_file_456"
        message.document = document
        message.answer = AsyncMock()
        update.message = message

        test_file_path = Path("/tmp/uploaded.html")
        file_obj.download_to_drive = AsyncMock(return_value=test_file_path)
        bot.get_file = AsyncMock(return_value=file_obj)
        context.bot = bot

        mock_read_html.return_value = "Extracted HTML content"

        # Create long content that will trigger Telegraph
        long_article = Article(
            title="Long HTML Document",
            sections=[
                Section(title="📊 Section 1", content="A" * 400),
                Section(title="🔍 Section 2", content="B" * 400),
                Section(title="📈 Section 3", content="C" * 400),
            ],
        )
        mock_format.return_value = long_article
        mock_async_create_page.return_value = "https://telegra.ph/long-html-document-789"

        # Execute workflow
        await file_callback(update, context)

        # Verify complete chain
        bot.get_file.assert_called_once_with("html_file_456")
        mock_read_html.assert_called_once_with(test_file_path)
        mock_format.assert_called_once_with("Extracted HTML content")

        # Verify Telegraph page creation for long content (via MessageResponse.send())
        mock_async_create_page.assert_called_once()

        # Verify response with Telegraph URL
        message.answer.assert_called_once_with("https://telegra.ph/long-html-document-789")
        mock_remove.assert_called_once_with(test_file_path)
