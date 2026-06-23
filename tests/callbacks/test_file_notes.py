from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from aiogram import Bot
from aiogram.types import Document
from aiogram.types import Message

from bot.callbacks.file_notes import file_callback


@pytest.mark.asyncio
@patch("bot.callbacks.file_notes.write_article", new_callable=AsyncMock)
@patch("bot.callbacks.file_notes.read_pdf_content")
async def test_file_callback_reads_pdf_with_injected_bot(mock_read_pdf_content, mock_write_article, tmp_path):
    file_path = tmp_path / "note.pdf"
    file_path.write_text("pdf bytes")
    mock_read_pdf_content.return_value = "pdf text"

    article = Mock()
    article.reply = AsyncMock()
    mock_write_article.return_value = article

    file = Mock()
    file.download_to_drive = AsyncMock(return_value=file_path)

    bot = Mock(spec=Bot)
    bot.get_file = AsyncMock(return_value=file)

    document = Mock(spec=Document)
    document.file_id = "file-id"

    message = Mock(spec=Message)
    message.document = document

    await file_callback(message, bot)

    bot.get_file.assert_awaited_once_with("file-id")
    mock_read_pdf_content.assert_called_once_with(file_path)
    mock_write_article.assert_awaited_once_with("pdf text")
    article.reply.assert_awaited_once_with(message)
    assert not file_path.exists()
