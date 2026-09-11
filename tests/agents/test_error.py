import json
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import httpx

from bot.agents.error import ErrorExplanation
from bot.agents.error import explain_error
from bot.agents.error import fallback_error_explanation


@patch("bot.agents.error.build_error_agent")
@patch("bot.agents.error.Runner.run", new_callable=AsyncMock)
async def test_explain_error_sends_allowlisted_structured_error_data(mock_run, mock_build_error_agent):
    expected = ErrorExplanation(
        user_message="外部服務暫時沒有回應，請稍後重送一次。",
        administrator_message="ValueError；請檢查輸入處理。",
    )
    result = Mock()
    result.final_output_as.return_value = expected
    mock_run.return_value = result
    agent = Mock()
    mock_build_error_agent.return_value = agent
    secret = "https://example.com/api?token=sensitive"
    error = ValueError(secret)

    explanation = await explain_error(error)

    assert explanation == expected
    payload = json.loads(mock_run.await_args.kwargs["input"])
    assert payload == {
        "error_type": "ValueError",
        "retryable": False,
    }
    assert secret not in mock_run.await_args.kwargs["input"]
    mock_run.assert_awaited_once_with(agent, input=mock_run.await_args.kwargs["input"])
    result.final_output_as.assert_called_once_with(ErrorExplanation)


def test_fallback_error_explanation_recommends_retry_for_transient_error():
    explanation = fallback_error_explanation(httpx.ReadTimeout("upstream timed out"))

    assert "稍後重新傳送一次" in explanation.user_message
    assert "ReadTimeout" in explanation.administrator_message
    assert "upstream timed out" not in explanation.administrator_message


def test_fallback_error_explanation_stops_retries_for_unknown_error():
    explanation = fallback_error_explanation(ValueError("invalid input"))

    assert "先不要重複傳送" in explanation.user_message
    assert "ValueError" not in explanation.user_message
    assert "ValueError" in explanation.administrator_message
    assert "invalid input" not in explanation.administrator_message
