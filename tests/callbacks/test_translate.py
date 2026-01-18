from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from telegram import Chat
from telegram import Message
from telegram import Update
from telegram import User

from bot.callbacks.translate import TranslationCallback


class TestTranslationCallback:
    def setup_method(self):
        self.user = User(id=123, is_bot=False, first_name="TestUser", username="testuser")
        self.chat = Chat(id=456, type="private")
        self.context = Mock()
        self.callback = TranslationCallback(lang="zh")

    @pytest.mark.asyncio
    async def test_translation_callback_no_message(self):
        update = Mock(spec=Update)
        update.message = None

        result = await self.callback(update, self.context)
        assert result is None

    @pytest.mark.asyncio
    async def test_translation_callback_empty_message(self):
        message = Mock(spec=Message)
        message.text = ""
        message.from_user = self.user
        message.reply_to_message = None

        update = Mock(spec=Update)
        update.message = message

        result = await self.callback(update, self.context)
        assert result is None

    @pytest.mark.asyncio
    @patch("bot.callbacks.translate.chains.translate")
    async def test_translation_callback_simple_text(self, mock_translate):
        mock_translate.return_value = "這是翻譯的內容"

        message = Mock(spec=Message)
        message.text = "This is content to translate"
        message.from_user = self.user
        message.reply_to_message = None
        message.reply_text = AsyncMock()

        update = Mock(spec=Update)
        update.message = message

        await self.callback(update, self.context)

        mock_translate.assert_called_once_with("This is content to translate", target_lang="zh")
        # MessageResponse.send() is called internally, which calls message.reply_text
        message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    @patch("bot.callbacks.translate.chains.translate")
    @patch("bot.callbacks.translate.get_processed_message_text")
    async def test_translation_callback_with_url(self, mock_get_processed, mock_translate):
        mock_get_processed.return_value = ("Content from URL", None)
        mock_translate.return_value = "URL內容的翻譯"

        message = Mock(spec=Message)
        message.text = "Translate this URL: https://example.com"
        message.from_user = self.user
        message.reply_to_message = None
        message.reply_text = AsyncMock()

        update = Mock(spec=Update)
        update.message = message

        await self.callback(update, self.context)

        mock_get_processed.assert_called_once_with(message, require_url=False)
        mock_translate.assert_called_once_with("Content from URL", target_lang="zh")
        # MessageResponse.send() is called internally
        message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    @patch("bot.presentation.async_create_page")
    @patch("bot.callbacks.translate.chains.translate")
    async def test_translation_callback_long_content(self, mock_translate, mock_async_create_page):
        long_translation = "這是一個很長的翻譯內容" * 100  # Longer than MAX_LENGTH (1000)
        mock_translate.return_value = long_translation
        mock_async_create_page.return_value = "https://telegra.ph/translation-page"

        message = Mock(spec=Message)
        message.text = "Long message to translate"
        message.from_user = self.user
        message.reply_to_message = None
        message.reply_text = AsyncMock()

        update = Mock(spec=Update)
        update.message = message

        await self.callback(update, self.context)

        mock_translate.assert_called_once_with("Long message to translate", target_lang="zh")
        # MessageResponse.send() will create Telegraph page for long content
        mock_async_create_page.assert_called_once()
        message.reply_text.assert_called_once_with("https://telegra.ph/translation-page")

    def test_translation_callback_init(self):
        callback = TranslationCallback(lang="en")
        assert callback.lang == "en"
