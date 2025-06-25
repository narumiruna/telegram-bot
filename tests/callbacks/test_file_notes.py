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
from telegram import Document
from telegram import File
from telegram import Message
from telegram import Update

from bot.callbacks.file_notes import MAX_LENGTH
from bot.callbacks.file_notes import file_callback
from bot.chains.formatter import Article
from bot.chains.formatter import Section


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
        message.reply_text = AsyncMock()
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

        # Verify response (short content should be sent as text)
        expected_text = str(sample_article)
        mock_update.message.reply_text.assert_called_once_with(expected_text)

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
        expected_text = str(sample_article)
        mock_update.message.reply_text.assert_called_once_with(expected_text)

    @pytest.mark.asyncio
    @patch("bot.callbacks.file_notes.read_pdf_content")
    @patch("bot.callbacks.file_notes.chains.format")
    @patch("bot.callbacks.file_notes.create_page")
    @patch("bot.callbacks.file_notes.os.remove")
    async def test_file_callback_pdf_success_long_content(
        self, mock_remove, mock_create_page, mock_format, mock_read_pdf, mock_update, mock_context
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
        mock_create_page.return_value = "https://telegra.ph/test-page-123"

        # Execute
        await file_callback(mock_update, mock_context)

        # Verify processing
        mock_read_pdf.assert_called_once_with(test_file_path)
        mock_format.assert_called_once_with("Long PDF content for testing")

        # Verify Telegraph page creation for long content
        expected_html = str(long_article).replace("\n", "<br>")
        mock_create_page.assert_called_once_with(title=long_article.title, html_content=expected_html)

        # Verify response with Telegraph URL
        mock_update.message.reply_text.assert_called_once_with("https://telegra.ph/test-page-123")

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
        mock_update.message.reply_text.assert_not_called()

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
        mock_update.message.reply_text.assert_called_once_with(str(sample_article))

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
        mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    @patch("bot.callbacks.file_notes.read_pdf_content")
    @patch("bot.callbacks.file_notes.os.remove")
    async def test_file_callback_pdf_read_error(self, mock_remove, mock_read_pdf, mock_update, mock_context):
        """Test PDF processing when read_pdf_content raises an error."""
        # Setup mocks
        test_file_path = Path("/tmp/test.pdf")
        mock_context.bot.get_file.return_value.download_to_drive.return_value = test_file_path
        mock_read_pdf.side_effect = Exception("PDF reading failed")

        # Execute - should raise exception since no error handling
        with pytest.raises(Exception, match="PDF reading failed"):
            await file_callback(mock_update, mock_context)

        # Verify file processing was attempted
        mock_read_pdf.assert_called_once_with(test_file_path)

        # File cleanup happens after content reading, so it won't be called if reading fails
        mock_remove.assert_not_called()

        # Verify no reply due to error
        mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    @patch("bot.callbacks.file_notes.read_html_content")
    @patch("bot.callbacks.file_notes.os.remove")
    async def test_file_callback_html_read_error(self, mock_remove, mock_read_html, mock_update, mock_context):
        """Test HTML processing when read_html_content raises an error."""
        # Setup mocks
        test_file_path = Path("/tmp/test.html")
        mock_context.bot.get_file.return_value.download_to_drive.return_value = test_file_path
        mock_read_html.side_effect = FileNotFoundError("HTML file not found")

        # Execute - should raise exception since no error handling
        with pytest.raises(FileNotFoundError, match="HTML file not found"):
            await file_callback(mock_update, mock_context)

        # Verify file processing was attempted
        mock_read_html.assert_called_once_with(test_file_path)

        # File cleanup happens after content reading, so it won't be called if reading fails
        mock_remove.assert_not_called()

        # Verify no reply due to error
        mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    @patch("bot.callbacks.file_notes.read_pdf_content")
    @patch("bot.callbacks.file_notes.chains.format")
    @patch("bot.callbacks.file_notes.os.remove")
    async def test_file_callback_format_chain_error(
        self, mock_remove, mock_format, mock_read_pdf, mock_update, mock_context
    ):
        """Test when chains.format raises an error."""
        # Setup mocks
        test_file_path = Path("/tmp/test.pdf")
        mock_context.bot.get_file.return_value.download_to_drive.return_value = test_file_path
        mock_read_pdf.return_value = "Valid PDF content"
        mock_format.side_effect = Exception("Format chain failed")

        # Execute - should raise exception since no error handling
        with pytest.raises(Exception, match="Format chain failed"):
            await file_callback(mock_update, mock_context)

        # Verify processing was attempted
        mock_read_pdf.assert_called_once_with(test_file_path)
        mock_format.assert_called_once_with("Valid PDF content")

        # Verify file cleanup happens before format chain
        mock_remove.assert_called_once_with(test_file_path)

        # Verify no reply due to format error
        mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    @patch("bot.callbacks.file_notes.read_pdf_content")
    @patch("bot.callbacks.file_notes.chains.format")
    @patch("bot.callbacks.file_notes.create_page")
    @patch("bot.callbacks.file_notes.os.remove")
    async def test_file_callback_telegraph_creation_error(
        self, mock_remove, mock_create_page, mock_format, mock_read_pdf, mock_update, mock_context
    ):
        """Test when Telegraph page creation fails."""
        # Setup mocks for long content
        long_article = Article(
            title="Long Document", sections=[Section(title="🔍 Long Section", content="A" * MAX_LENGTH)]
        )

        test_file_path = Path("/tmp/test.pdf")
        mock_context.bot.get_file.return_value.download_to_drive.return_value = test_file_path
        mock_read_pdf.return_value = "Long PDF content"
        mock_format.return_value = long_article
        mock_create_page.side_effect = Exception("Telegraph creation failed")

        # Execute - should raise exception since no error handling
        with pytest.raises(Exception, match="Telegraph creation failed"):
            await file_callback(mock_update, mock_context)

        # Verify processing
        mock_read_pdf.assert_called_once_with(test_file_path)
        mock_format.assert_called_once_with("Long PDF content")
        mock_create_page.assert_called_once()

        # Verify file cleanup happens before Telegraph creation
        mock_remove.assert_called_once_with(test_file_path)

        # Verify no reply due to Telegraph error
        mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    @patch("bot.callbacks.file_notes.read_pdf_content")
    @patch("bot.callbacks.file_notes.chains.format")
    @patch("bot.callbacks.file_notes.os.remove")
    async def test_file_callback_reply_text_error(
        self, mock_remove, mock_format, mock_read_pdf, mock_update, mock_context, sample_article
    ):
        """Test when reply_text fails."""
        # Setup mocks
        test_file_path = Path("/tmp/test.pdf")
        mock_context.bot.get_file.return_value.download_to_drive.return_value = test_file_path
        mock_read_pdf.return_value = "PDF content"
        mock_format.return_value = sample_article
        mock_update.message.reply_text.side_effect = Exception("Reply failed")

        # Execute - should raise exception since no error handling
        with pytest.raises(Exception, match="Reply failed"):
            await file_callback(mock_update, mock_context)

        # Verify processing completed before reply failure
        mock_read_pdf.assert_called_once_with(test_file_path)
        mock_format.assert_called_once_with("PDF content")
        mock_update.message.reply_text.assert_called_once()

        # Verify file cleanup happens before reply
        mock_remove.assert_called_once_with(test_file_path)

    @pytest.mark.asyncio
    async def test_file_callback_download_error(self, mock_update, mock_context):
        """Test when file download fails."""
        # Setup mocks
        mock_context.bot.get_file.return_value.download_to_drive.side_effect = Exception("Download failed")

        # Execute - should raise exception since no error handling
        with pytest.raises(Exception, match="Download failed"):
            await file_callback(mock_update, mock_context)

        # Verify download was attempted
        mock_context.bot.get_file.assert_called_once_with("test_file_id")
        mock_context.bot.get_file.return_value.download_to_drive.assert_called_once()

        # Verify no reply due to download error
        mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_file_callback_get_file_error(self, mock_update, mock_context):
        """Test when getting file from Telegram fails."""
        # Setup mocks
        mock_context.bot.get_file.side_effect = Exception("Get file failed")

        # Execute - should raise exception since no error handling
        with pytest.raises(Exception, match="Get file failed"):
            await file_callback(mock_update, mock_context)

        # Verify get_file was attempted
        mock_context.bot.get_file.assert_called_once_with("test_file_id")

        # Verify no reply due to get_file error
        mock_update.message.reply_text.assert_not_called()


class TestMaxLengthConstant:
    """Test the MAX_LENGTH constant usage."""

    def test_max_length_value(self):
        """Test that MAX_LENGTH has expected value."""
        assert MAX_LENGTH == 1_000

    def test_max_length_boundary_conditions(self, sample_article):
        """Test length boundary conditions."""
        # Create content exactly at boundary
        boundary_content = "A" * MAX_LENGTH
        assert len(boundary_content) == MAX_LENGTH

        # Create content over boundary
        over_boundary_content = "A" * (MAX_LENGTH + 1)
        assert len(over_boundary_content) > MAX_LENGTH

    @pytest.fixture
    def sample_article(self):
        """Create a sample Article for boundary testing."""
        return Article(title="Test", sections=[Section(title="Test Section", content="Test content")])


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
        message.reply_text = AsyncMock()
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

        # Verify response
        expected_response = "📝 Processed Document\n\n📄 Content\nFormatted content"
        message.reply_text.assert_called_once_with(expected_response)

    @pytest.mark.asyncio
    @patch("bot.callbacks.file_notes.read_html_content")
    @patch("bot.callbacks.file_notes.chains.format")
    @patch("bot.callbacks.file_notes.create_page")
    @patch("bot.callbacks.file_notes.os.remove")
    async def test_complete_html_workflow_with_telegraph(
        self, mock_remove, mock_create_page, mock_format, mock_read_html
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
        message.reply_text = AsyncMock()
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
        mock_create_page.return_value = "https://telegra.ph/long-html-document-789"

        # Execute workflow
        await file_callback(update, context)

        # Verify complete chain
        bot.get_file.assert_called_once_with("html_file_456")
        mock_read_html.assert_called_once_with(test_file_path)
        mock_format.assert_called_once_with("Extracted HTML content")

        # Verify Telegraph page creation for long content
        expected_html = str(long_article).replace("\n", "<br>")
        mock_create_page.assert_called_once_with(title="Long HTML Document", html_content=expected_html)

        # Verify response with Telegraph URL
        message.reply_text.assert_called_once_with("https://telegra.ph/long-html-document-789")
        mock_remove.assert_called_once_with(test_file_path)

    @pytest.mark.asyncio
    @patch("bot.callbacks.file_notes.os.remove")
    async def test_file_extension_case_sensitivity(self, mock_remove):
        """Test file extension handling with different cases."""
        # Test different file extensions - code checks exact case: .pdf and .html
        test_cases = [
            ("/tmp/test.pdf", True),  # Should match PDF
            ("/tmp/test.html", True),  # Should match HTML
            ("/tmp/test.PDF", False),  # Should NOT match (case sensitive)
            ("/tmp/test.Html", False),  # Should NOT match (case sensitive)
            ("/tmp/test.HTM", False),  # Should not match (not .html)
            ("/tmp/test.txt", False),  # Should not match
            ("/tmp/test", False),  # Should not match (no extension)
        ]

        for file_path_str, should_process in test_cases:
            # Setup mocks for each test case
            update = Mock(spec=Update)
            message = Mock(spec=Message)
            document = Mock(spec=Document)
            context = Mock()
            bot = Mock()
            file_obj = Mock(spec=File)

            document.file_id = "test_file"
            message.document = document
            message.reply_text = AsyncMock()
            update.message = message

            test_file_path = Path(file_path_str)
            file_obj.download_to_drive = AsyncMock(return_value=test_file_path)
            bot.get_file = AsyncMock(return_value=file_obj)
            context.bot = bot

            with (
                patch("bot.callbacks.file_notes.read_pdf_content") as mock_read_pdf,
                patch("bot.callbacks.file_notes.read_html_content") as mock_read_html,
                patch("bot.callbacks.file_notes.chains.format") as mock_format,
            ):
                # Mock the format chain for successful processing
                mock_read_pdf.return_value = "PDF content"
                mock_read_html.return_value = "HTML content"
                mock_format.return_value = Article(title="Test", sections=[Section(title="Test", content="Content")])

                # Execute
                await file_callback(update, context)

                # Verify cleanup always happens
                mock_remove.assert_called_with(test_file_path)
                mock_remove.reset_mock()

                # Verify processing based on exact extension match
                if should_process:
                    if test_file_path.suffix == ".pdf":
                        mock_read_pdf.assert_called_once_with(test_file_path)
                        mock_read_html.assert_not_called()
                    elif test_file_path.suffix == ".html":
                        mock_read_html.assert_called_once_with(test_file_path)
                        mock_read_pdf.assert_not_called()
                else:
                    mock_read_pdf.assert_not_called()
                    mock_read_html.assert_not_called()

                # Reset mocks for next iteration
                mock_read_pdf.reset_mock()
                mock_read_html.reset_mock()
