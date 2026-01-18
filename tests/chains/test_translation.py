from unittest.mock import patch

import pytest

from bot.chains.translation import translate
from bot.chains.translation import translate_and_explain
from bot.chains.translation import translate_to_taiwanese


class TestTranslation:
    @pytest.mark.asyncio
    @patch("bot.chains.translation.lazy_run")
    async def test_translate_to_taiwanese(self, mock_lazy_run):
        mock_lazy_run.return_value = "這是翻譯的內容"

        result = await translate_to_taiwanese("This is content to translate")

        mock_lazy_run.assert_called_once()
        call_args = mock_lazy_run.call_args[0][0]
        assert "你是翻譯專家" in call_args
        assert "This is content to translate" in call_args
        assert "台灣正體中文" in call_args
        assert result == "這是翻譯的內容"

    @pytest.mark.asyncio
    @patch("bot.chains.translation.lazy_run")
    async def test_translate(self, mock_lazy_run):
        mock_lazy_run.return_value = '"This is translated content"'

        result = await translate("這是要翻譯的內容", target_lang="English")

        mock_lazy_run.assert_called_once()

        # Check the user_prompt argument
        user_prompt = mock_lazy_run.call_args[0][0]
        assert user_prompt == '"""這是要翻譯的內容"""'

        # Check the instructions argument
        instructions = mock_lazy_run.call_args[1]["instructions"]
        assert "Translate the text" in instructions
        assert "into English" in instructions

        # Check that quotes are stripped from result
        assert result == "This is translated content"

    @pytest.mark.asyncio
    @patch("bot.chains.translation.lazy_run")
    async def test_translate_without_quotes(self, mock_lazy_run):
        mock_lazy_run.return_value = "This is translated content"

        result = await translate("這是要翻譯的內容", target_lang="English")

        assert result == "This is translated content"

    @pytest.mark.asyncio
    @patch("bot.chains.translation.lazy_run")
    async def test_translate_and_explain(self, mock_lazy_run):
        mock_lazy_run.return_value = '"This is translated content with explanation"'

        result = await translate_and_explain("これは日本語です", target_lang="English")

        mock_lazy_run.assert_called_once()

        # Check the user_prompt argument
        user_prompt = mock_lazy_run.call_args[0][0]
        assert user_prompt == '"""これは日本語です"""'

        # Check the instructions argument
        instructions = mock_lazy_run.call_args[1]["instructions"]
        assert "Translate the text" in instructions
        assert "into English" in instructions
        assert "explanation of grammar" in instructions
        assert "example sentences" in instructions

        # Check that quotes are stripped from result
        assert result == "This is translated content with explanation"

    @pytest.mark.asyncio
    @patch("bot.chains.translation.lazy_run")
    async def test_translate_different_languages(self, mock_lazy_run):
        mock_lazy_run.return_value = "Translated content"

        # Test with different target languages
        await translate("Hello", target_lang="Japanese")
        await translate("Hello", target_lang="French")
        await translate("Hello", target_lang="German")

        assert mock_lazy_run.call_count == 3

        # Check that different languages are used in instructions
        calls = mock_lazy_run.call_args_list
        assert "into Japanese" in calls[0][1]["instructions"]
        assert "into French" in calls[1][1]["instructions"]
        assert "into German" in calls[2][1]["instructions"]
