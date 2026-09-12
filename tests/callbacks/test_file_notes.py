import asyncio
import threading
from collections.abc import AsyncIterator
from datetime import UTC
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest
from aiogram import Bot
from aiogram.types import Chat
from aiogram.types import Document
from aiogram.types import File
from aiogram.types import Message

from bot.agents.writer import Article
from bot.callbacks.file_notes import _read_document
from bot.callbacks.file_notes import file_callback


@pytest.fixture
async def bot() -> AsyncIterator[Bot]:
    async with Bot(token="123456:TEST_TOKEN") as test_bot:
        with patch.object(
            test_bot,
            "get_file",
            new_callable=AsyncMock,
            return_value=File(file_id="file-id", file_unique_id="unique-id", file_path="documents/remote.bin"),
        ):
            yield test_bot


@pytest.fixture
def message() -> Message:
    return Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=123, type="private"),
        document=Document(file_id="file-id", file_unique_id="unique-id", file_name="note.pdf"),
    )


@patch("bot.callbacks.file_notes.html_to_markdown")
def test_read_document_converts_html_bytes(mock_html_to_markdown, tmp_path):
    file_path = tmp_path / "note.html"
    html = b"<h1>Notes</h1><p>Body</p>"
    file_path.write_bytes(html)
    mock_html_to_markdown.return_value = "html text"

    assert _read_document(file_path) == "html text"
    mock_html_to_markdown.assert_called_once_with(html)


@pytest.mark.parametrize(
    ("file_name", "parser_name"),
    [
        ("note.pdf", "read_pdf_content"),
        ("../../note.PDF", "read_pdf_content"),
        ("note.html", "html_to_markdown"),
        ("note.HTML", "html_to_markdown"),
    ],
)
async def test_file_callback_downloads_and_reads_document(bot, message, file_name, parser_name):
    message = message.model_copy(update={"document": message.document.model_copy(update={"file_name": file_name})})
    downloaded_paths = []
    event_loop_thread = threading.get_ident()
    document_bytes = b"document bytes"

    async def download_file(file_path, *, destination, **kwargs):
        assert file_path == "documents/remote.bin"
        assert destination.name == f"document{Path(file_name).suffix.lower()}"
        destination.write_bytes(document_bytes)
        downloaded_paths.append(destination)

    def parse_document(content):
        assert threading.get_ident() != event_loop_thread
        assert (content.read_bytes() if isinstance(content, Path) else content) == document_bytes
        return "document text"

    article = Article(title="Notes", summary="Summary", sections=[])
    with (
        patch.object(
            bot,
            "get_file",
            new_callable=AsyncMock,
            return_value=File(file_id="file-id", file_unique_id="unique-id", file_path="documents/remote.bin"),
        ) as get_file,
        patch.object(bot, "download_file", new_callable=AsyncMock, side_effect=download_file) as download,
        patch(f"bot.callbacks.file_notes.{parser_name}", side_effect=parse_document) as parser,
        patch("bot.callbacks.file_notes.write_article", new_callable=AsyncMock, return_value=article) as write_article,
        patch.object(Article, "reply", new_callable=AsyncMock) as reply,
    ):
        await file_callback(message, bot)

    get_file.assert_awaited_once_with("file-id")
    download.assert_awaited_once()
    parser.assert_called_once()
    write_article.assert_awaited_once_with("document text")
    reply.assert_awaited_once_with(message)
    assert len(downloaded_paths) == 1
    assert not downloaded_paths[0].parent.exists()


@pytest.mark.parametrize("file_name", [None, "note", "note.txt", "note.exe"])
async def test_file_callback_ignores_unsupported_documents(bot, message, file_name):
    message = message.model_copy(update={"document": message.document.model_copy(update={"file_name": file_name})})
    with (
        patch.object(bot, "get_file", new_callable=AsyncMock) as get_file,
        patch.object(bot, "download", new_callable=AsyncMock) as download,
        patch("bot.callbacks.file_notes.write_article", new_callable=AsyncMock) as write_article,
    ):
        await file_callback(message, bot)

    get_file.assert_not_awaited()
    download.assert_not_awaited()
    write_article.assert_not_awaited()


async def test_file_callback_ignores_messages_without_documents(bot, message):
    with patch.object(bot, "download", new_callable=AsyncMock) as download:
        await file_callback(message.model_copy(update={"document": None}), bot)

    download.assert_not_awaited()


@pytest.mark.parametrize("stage", ["download", "read", "write", "reply"])
@pytest.mark.parametrize("error_type", [RuntimeError, asyncio.CancelledError])
async def test_file_callback_cleans_up_on_failure_or_cancellation(bot, message, stage, error_type):
    downloaded_paths = []
    error = error_type("interrupted")

    async def download_document(document, *, destination):
        destination.write_bytes(b"partial document")
        downloaded_paths.append(destination)
        if stage == "download":
            raise error

    article = Article(title="Notes", summary="Summary", sections=[])
    with (
        patch.object(bot, "download", new_callable=AsyncMock, side_effect=download_document),
        patch(
            "bot.callbacks.file_notes._read_document",
            return_value="document text",
            side_effect=error if stage == "read" else None,
        ),
        patch(
            "bot.callbacks.file_notes.write_article",
            new_callable=AsyncMock,
            return_value=article,
            side_effect=error if stage == "write" else None,
        ),
        patch.object(Article, "reply", new_callable=AsyncMock, side_effect=error if stage == "reply" else None),
        pytest.raises(error_type) as raised,
    ):
        await file_callback(message, bot)

    assert raised.value is error
    assert len(downloaded_paths) == 1
    assert not downloaded_paths[0].parent.exists()


async def test_file_callback_skips_empty_documents(bot, message):
    downloaded_paths = []

    async def download_document(document, *, destination):
        destination.touch()
        downloaded_paths.append(destination)

    with (
        patch.object(bot, "download", new_callable=AsyncMock, side_effect=download_document),
        patch("bot.callbacks.file_notes._read_document", return_value=""),
        patch("bot.callbacks.file_notes.write_article", new_callable=AsyncMock) as write_article,
    ):
        await file_callback(message, bot)

    write_article.assert_not_awaited()
    assert len(downloaded_paths) == 1
    assert not downloaded_paths[0].parent.exists()
