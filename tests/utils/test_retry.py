import httpx2
import pytest
from openai import APIStatusError

from bot.utils.retry import is_retryable_error


def _make_openai_status_error(status_code: int) -> APIStatusError:
    request = httpx2.Request("POST", "https://model.example.invalid")
    response = httpx2.Response(status_code, request=request)
    return APIStatusError("provider request failed", response=response, body=None)


@pytest.mark.parametrize("status_code", [429, 500, 503])
def test_is_retryable_error_accepts_transient_openai_statuses(status_code):
    assert is_retryable_error(_make_openai_status_error(status_code))


def test_is_retryable_error_rejects_non_transient_openai_status():
    assert not is_retryable_error(_make_openai_status_error(400))
