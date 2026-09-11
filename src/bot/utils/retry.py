import httpx
from openai import APIStatusError


def is_retryable_error(error: BaseException) -> bool:
    """
    Determine if an error should trigger a retry attempt.

    Args:
        error: The exception that occurred

    Returns:
        True if the error is retryable, False otherwise
    """
    # Network and timeout errors (always retryable)
    if isinstance(error, httpx.TimeoutException | httpx.ConnectTimeout | httpx.ReadTimeout):
        return True

    if isinstance(error, httpx.NetworkError):
        return True

    # HTTP errors - retry on server errors (5xx) and rate limiting (429)
    if isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code
        return status_code >= 500 or status_code == 429

    # OpenAI status errors use httpx2 responses, so classify their status codes separately.
    if isinstance(error, APIStatusError):
        return error.status_code >= 500 or error.status_code == 429

    # Connection errors from other libraries (string matching)
    return "connection" in str(error).lower() or "timeout" in str(error).lower()
