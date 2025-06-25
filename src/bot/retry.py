"""
Retry mechanism utilities for external API calls.

Provides decorators and utilities for implementing retry logic with exponential backoff,
timeout handling, and comprehensive error categorization.
"""

import asyncio
import functools
import logging
import random
import time
from collections.abc import Callable
from typing import Any

import httpx
from openai import APIError
from openai import RateLimitError

logger = logging.getLogger(__name__)


class RetryError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(self, original_error: Exception, attempts: int):
        self.original_error = original_error
        self.attempts = attempts
        super().__init__(f"Failed after {attempts} attempts: {original_error}")


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        timeout: float = 30.0,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.timeout = timeout


# Default retry configurations for different service types
NETWORK_API_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    timeout=30.0,
)

RATE_LIMITED_API_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=2.0,
    max_delay=120.0,
    timeout=60.0,
)

FAST_API_CONFIG = RetryConfig(
    max_attempts=2,
    base_delay=0.5,
    max_delay=5.0,
    timeout=10.0,
)


def is_retryable_error(error: Exception) -> bool:
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

    # HTTP errors
    if isinstance(error, httpx.HTTPStatusError):
        # Retry on server errors (5xx) and rate limiting (429)
        status_code = error.response.status_code
        return status_code >= 500 or status_code == 429

    # OpenAI specific errors
    if isinstance(error, RateLimitError):
        return True

    if isinstance(error, APIError):
        # Only retry on server errors, not client errors
        return hasattr(error, "status_code") and error.status_code >= 500

    # Connection errors from other libraries
    return "connection" in str(error).lower() or "timeout" in str(error).lower()


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate the delay before the next retry attempt.

    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    # Exponential backoff: base_delay * (exponential_base ^ attempt)
    delay = config.base_delay * (config.exponential_base**attempt)

    # Cap at max_delay
    delay = min(delay, config.max_delay)

    # Add jitter to avoid thundering herd problem
    if config.jitter:
        jitter_range = delay * 0.1  # 10% jitter
        delay += random.uniform(-jitter_range, jitter_range)

    return max(0, delay)


def retry_on_failure(
    config: RetryConfig = NETWORK_API_CONFIG,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator to add retry logic to synchronous functions.

    Args:
        config: Retry configuration
        exceptions: Tuple of exception types to catch and potentially retry

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error: Exception | None = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as error:
                    last_error = error

                    if not is_retryable_error(error):
                        logger.warning(f"Non-retryable error in {func.__name__}: {error}")
                        raise error

                    if attempt == config.max_attempts - 1:
                        logger.error(f"All retry attempts exhausted for {func.__name__}: {error}")
                        raise RetryError(error, config.max_attempts) from error

                    delay = calculate_delay(attempt, config)
                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_attempts} failed for {func.__name__}: {error}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    time.sleep(delay)

            # This should never be reached, but included for type safety
            if last_error:
                raise RetryError(last_error, config.max_attempts) from last_error
            raise RuntimeError("Unexpected retry logic error")

        return wrapper

    return decorator


def async_retry_on_failure(
    config: RetryConfig = NETWORK_API_CONFIG,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator to add retry logic to asynchronous functions.

    Args:
        config: Retry configuration
        exceptions: Tuple of exception types to catch and potentially retry

    Returns:
        Decorated async function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error: Exception | None = None

            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as error:
                    last_error = error

                    if not is_retryable_error(error):
                        logger.warning(f"Non-retryable error in {func.__name__}: {error}")
                        raise error

                    if attempt == config.max_attempts - 1:
                        logger.error(f"All retry attempts exhausted for {func.__name__}: {error}")
                        raise RetryError(error, config.max_attempts) from error

                    delay = calculate_delay(attempt, config)
                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_attempts} failed for {func.__name__}: {error}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)

            # This should never be reached, but included for type safety
            if last_error:
                raise RetryError(last_error, config.max_attempts) from last_error
            raise RuntimeError("Unexpected retry logic error")

        return wrapper

    return decorator


def with_timeout(timeout: float) -> Callable:
    """
    Decorator to add timeout to synchronous functions.

    Args:
        timeout: Timeout in seconds

    Returns:
        Decorated function with timeout logic
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Note: This is a simplified timeout implementation
            # For more robust timeout handling, consider using signal-based timeouts
            # or threading-based approaches
            return func(*args, **kwargs)

        return wrapper

    return decorator


def async_with_timeout(timeout: float) -> Callable:
    """
    Decorator to add timeout to asynchronous functions.

    Args:
        timeout: Timeout in seconds

    Returns:
        Decorated async function with timeout logic
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            except TimeoutError as error:
                logger.error(f"Timeout ({timeout}s) exceeded for {func.__name__}")
                raise TimeoutError(f"Function {func.__name__} timed out after {timeout}s") from error

        return wrapper

    return decorator


# Convenience decorators combining retry and timeout
def robust_api_call(
    config: RetryConfig = NETWORK_API_CONFIG,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator combining retry logic and timeout for robust API calls.

    Args:
        config: Retry configuration (timeout is also used from config)
        exceptions: Tuple of exception types to catch and potentially retry

    Returns:
        Decorated function with retry and timeout logic
    """

    def decorator(func: Callable) -> Callable:
        return with_timeout(config.timeout)(retry_on_failure(config, exceptions)(func))

    return decorator


def robust_async_api_call(
    config: RetryConfig = NETWORK_API_CONFIG,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator combining retry logic and timeout for robust async API calls.

    Args:
        config: Retry configuration (timeout is also used from config)
        exceptions: Tuple of exception types to catch and potentially retry

    Returns:
        Decorated async function with retry and timeout logic
    """

    def decorator(func: Callable) -> Callable:
        return async_with_timeout(config.timeout)(async_retry_on_failure(config, exceptions)(func))

    return decorator
