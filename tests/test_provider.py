from unittest.mock import Mock
from unittest.mock import patch

from bot.provider import get_openai_model
from bot.settings import settings


def test_get_openai_model_builds_responses_model(monkeypatch):
    monkeypatch.setattr(settings, "openai_model", "test-model")
    client = Mock()
    model = Mock()

    with (
        patch("bot.provider.AsyncOpenAI", return_value=client) as openai_client,
        patch("bot.provider.OpenAIResponsesModel", return_value=model) as responses_model,
    ):
        result = get_openai_model()

    assert result is model
    openai_client.assert_called_once_with()
    responses_model.assert_called_once_with("test-model", openai_client=client)
