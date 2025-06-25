"""
Comprehensive tests for retry mechanism utilities.

Tests retry logic, exponential backoff, timeout handling, error categorization,
and integration with various external API scenarios.
"""

import asyncio
import time
from unittest.mock import Mock

import httpx
import pytest
from openai import APIError
from openai import RateLimitError

from bot.retry import FAST_API_CONFIG
from bot.retry import NETWORK_API_CONFIG
from bot.retry import RATE_LIMITED_API_CONFIG
from bot.retry import RetryConfig
from bot.retry import RetryError
from bot.retry import async_retry_on_failure
from bot.retry import async_with_timeout
from bot.retry import calculate_delay
from bot.retry import is_retryable_error
from bot.retry import retry_on_failure
from bot.retry import robust_api_call
from bot.retry import robust_async_api_call
from bot.retry import with_timeout


class TestRetryConfig:
    def test_default_config(self):
        """Test default retry configuration values"""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert config.timeout == 30.0

    def test_custom_config(self):
        """Test custom retry configuration"""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False,
            timeout=60.0,
        )
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is False
        assert config.timeout == 60.0

    def test_predefined_configs(self):
        """Test predefined configuration constants"""
        assert NETWORK_API_CONFIG.max_attempts == 3
        assert NETWORK_API_CONFIG.timeout == 30.0

        assert RATE_LIMITED_API_CONFIG.max_attempts == 5
        assert RATE_LIMITED_API_CONFIG.max_delay == 120.0

        assert FAST_API_CONFIG.max_attempts == 2
        assert FAST_API_CONFIG.timeout == 10.0


class TestErrorCategorization:
    def test_retryable_network_errors(self):
        """Test that network errors are categorized as retryable"""
        # httpx network errors
        assert is_retryable_error(httpx.TimeoutException("Timeout"))
        assert is_retryable_error(httpx.ConnectTimeout("Connect timeout"))
        assert is_retryable_error(httpx.ReadTimeout("Read timeout"))
        assert is_retryable_error(httpx.NetworkError("Network error"))

    def test_retryable_http_status_errors(self):
        """Test that certain HTTP status errors are retryable"""
        # Mock response for HTTP status errors
        response_500 = Mock(status_code=500)
        response_502 = Mock(status_code=502)
        response_503 = Mock(status_code=503)
        response_429 = Mock(status_code=429)

        assert is_retryable_error(httpx.HTTPStatusError("Server error", request=Mock(), response=response_500))
        assert is_retryable_error(httpx.HTTPStatusError("Bad gateway", request=Mock(), response=response_502))
        assert is_retryable_error(httpx.HTTPStatusError("Service unavailable", request=Mock(), response=response_503))
        assert is_retryable_error(httpx.HTTPStatusError("Rate limited", request=Mock(), response=response_429))

    def test_non_retryable_http_status_errors(self):
        """Test that client errors are not retryable"""
        response_400 = Mock(status_code=400)
        response_401 = Mock(status_code=401)
        response_403 = Mock(status_code=403)
        response_404 = Mock(status_code=404)

        assert not is_retryable_error(httpx.HTTPStatusError("Bad request", request=Mock(), response=response_400))
        assert not is_retryable_error(httpx.HTTPStatusError("Unauthorized", request=Mock(), response=response_401))
        assert not is_retryable_error(httpx.HTTPStatusError("Forbidden", request=Mock(), response=response_403))
        assert not is_retryable_error(httpx.HTTPStatusError("Not found", request=Mock(), response=response_404))

    def test_retryable_openai_errors(self):
        """Test OpenAI API error categorization"""
        # Rate limit errors should be retryable
        mock_response = Mock()
        mock_response.status_code = 429
        assert is_retryable_error(RateLimitError("Rate limited", response=mock_response, body=None))

        # Server errors should be retryable
        mock_request = Mock()
        server_error = APIError("Server error", request=mock_request, body=None)
        server_error.status_code = 500  # type: ignore[attr-defined]
        assert is_retryable_error(server_error)

    def test_non_retryable_openai_errors(self):
        """Test non-retryable OpenAI errors"""
        # Client errors should not be retryable
        mock_request = Mock()
        client_error = APIError("Invalid API key", request=mock_request, body=None)
        client_error.status_code = 401  # type: ignore[attr-defined]
        assert not is_retryable_error(client_error)

    def test_connection_error_detection(self):
        """Test detection of connection errors by string matching"""
        connection_error = Exception("Connection refused")
        timeout_error = Exception("Request timeout")

        assert is_retryable_error(connection_error)
        assert is_retryable_error(timeout_error)

    def test_unknown_errors_not_retryable(self):
        """Test that unknown errors are not retryable by default"""
        unknown_error = ValueError("Some unrelated error")
        assert not is_retryable_error(unknown_error)


class TestDelayCalculation:
    def test_exponential_backoff(self):
        """Test exponential backoff calculation"""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)

        assert calculate_delay(0, config) == 1.0  # 1.0 * 2^0
        assert calculate_delay(1, config) == 2.0  # 1.0 * 2^1
        assert calculate_delay(2, config) == 4.0  # 1.0 * 2^2
        assert calculate_delay(3, config) == 8.0  # 1.0 * 2^3

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay"""
        config = RetryConfig(base_delay=1.0, max_delay=5.0, exponential_base=2.0, jitter=False)

        assert calculate_delay(10, config) == 5.0  # Should be capped at max_delay

    def test_jitter_variation(self):
        """Test that jitter adds variation to delay"""
        config = RetryConfig(base_delay=10.0, jitter=True)

        # With jitter, delays should vary slightly
        delays = [calculate_delay(1, config) for _ in range(10)]

        # All delays should be close to expected value (20.0) but slightly different
        for delay in delays:
            assert 18.0 <= delay <= 22.0  # Within 10% jitter range

        # Should have some variation (not all identical)
        assert len({f"{d:.3f}" for d in delays}) > 1

    def test_jitter_disabled(self):
        """Test that jitter can be disabled"""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)

        # Without jitter, delays should be identical
        delays = [calculate_delay(1, config) for _ in range(5)]
        assert all(d == 2.0 for d in delays)

    def test_delay_never_negative(self):
        """Test that calculated delay is never negative"""
        config = RetryConfig(base_delay=0.1, jitter=True)

        # Even with jitter, delay should never be negative
        for attempt in range(10):
            delay = calculate_delay(attempt, config)
            assert delay >= 0


class TestSyncRetryDecorator:
    def test_successful_call_no_retry(self):
        """Test that successful calls don't trigger retry"""
        call_count = [0]

        @retry_on_failure(RetryConfig(max_attempts=3))
        def successful_function():
            call_count[0] += 1
            return "success"

        result = successful_function()
        assert result == "success"
        assert call_count[0] == 1

    def test_retry_on_retryable_error(self):
        """Test retry behavior on retryable errors"""
        call_count = [0]

        @retry_on_failure(RetryConfig(max_attempts=3, base_delay=0.1))
        def failing_function():
            call_count[0] += 1
            if call_count[0] < 3:
                raise httpx.NetworkError("Network error")
            return "success"

        start_time = time.time()
        result = failing_function()
        elapsed_time = time.time() - start_time

        assert result == "success"
        assert call_count[0] == 3
        assert elapsed_time >= 0.1  # Should have waited for retry

    def test_non_retryable_error_immediate_failure(self):
        """Test that non-retryable errors fail immediately"""
        call_count = [0]

        @retry_on_failure(RetryConfig(max_attempts=3))
        def failing_function():
            call_count[0] += 1
            response = Mock(status_code=400)
            raise httpx.HTTPStatusError("Bad request", request=Mock(), response=response)

        with pytest.raises(httpx.HTTPStatusError):
            failing_function()

        assert call_count[0] == 1  # Should not retry

    def test_retry_exhaustion_raises_retry_error(self):
        """Test that exhausted retries raise RetryError"""
        call_count = [0]

        @retry_on_failure(RetryConfig(max_attempts=2, base_delay=0.1))
        def always_failing_function():
            call_count[0] += 1
            raise httpx.NetworkError("Network error")

        with pytest.raises(RetryError) as exc_info:
            always_failing_function()

        assert call_count[0] == 2
        assert exc_info.value.attempts == 2
        assert isinstance(exc_info.value.original_error, httpx.NetworkError)

    def test_custom_exception_types(self):
        """Test retry with custom exception types"""
        call_count = [0]

        @retry_on_failure(RetryConfig(max_attempts=2, base_delay=0.1), exceptions=(httpx.NetworkError,))
        def custom_error_function():
            call_count[0] += 1
            if call_count[0] == 1:
                raise httpx.NetworkError("Custom network error")
            return "success"

        result = custom_error_function()
        assert result == "success"
        assert call_count[0] == 2

    def test_unhandled_exception_not_caught(self):
        """Test that unspecified exception types are not caught"""

        @retry_on_failure(RetryConfig(max_attempts=3), exceptions=(ValueError,))
        def type_error_function():
            raise TypeError("Type error")

        with pytest.raises(TypeError):
            type_error_function()


class TestAsyncRetryDecorator:
    @pytest.mark.asyncio
    async def test_successful_async_call_no_retry(self):
        """Test that successful async calls don't trigger retry"""
        call_count = [0]

        @async_retry_on_failure(RetryConfig(max_attempts=3))
        async def successful_async_function():
            call_count[0] += 1
            return "success"

        result = await successful_async_function()
        assert result == "success"
        assert call_count[0] == 1

    @pytest.mark.asyncio
    async def test_async_retry_on_retryable_error(self):
        """Test async retry behavior on retryable errors"""
        call_count = [0]

        @async_retry_on_failure(RetryConfig(max_attempts=3, base_delay=0.1))
        async def failing_async_function():
            call_count[0] += 1
            if call_count[0] < 3:
                raise httpx.NetworkError("Network error")
            return "success"

        start_time = time.time()
        result = await failing_async_function()
        elapsed_time = time.time() - start_time

        assert result == "success"
        assert call_count[0] == 3
        assert elapsed_time >= 0.1  # Should have waited for retry

    @pytest.mark.asyncio
    async def test_async_retry_exhaustion(self):
        """Test async retry exhaustion raises RetryError"""
        call_count = [0]

        @async_retry_on_failure(RetryConfig(max_attempts=2, base_delay=0.1))
        async def always_failing_async_function():
            call_count[0] += 1
            raise httpx.NetworkError("Network error")

        with pytest.raises(RetryError) as exc_info:
            await always_failing_async_function()

        assert call_count[0] == 2
        assert exc_info.value.attempts == 2


class TestTimeoutDecorators:
    def test_sync_timeout_success(self):
        """Test sync timeout decorator with successful function"""

        @with_timeout(1.0)
        def quick_function():
            return "success"

        result = quick_function()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_async_timeout_success(self):
        """Test async timeout decorator with successful function"""

        @async_with_timeout(1.0)
        async def quick_async_function():
            return "success"

        result = await quick_async_function()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_async_timeout_failure(self):
        """Test async timeout decorator with slow function"""

        @async_with_timeout(0.1)
        async def slow_async_function():
            await asyncio.sleep(0.2)
            return "success"

        with pytest.raises(TimeoutError) as exc_info:
            await slow_async_function()

        assert "timed out after 0.1s" in str(exc_info.value)


class TestRobustApiCallDecorators:
    def test_robust_api_call_combines_retry_and_timeout(self):
        """Test that robust_api_call combines retry and timeout"""
        call_count = [0]

        @robust_api_call(RetryConfig(max_attempts=2, base_delay=0.1, timeout=1.0))
        def api_function():
            call_count[0] += 1
            if call_count[0] == 1:
                raise httpx.NetworkError("Network error")
            return "success"

        result = api_function()
        assert result == "success"
        assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_robust_async_api_call_combines_retry_and_timeout(self):
        """Test that robust_async_api_call combines retry and timeout"""
        call_count = [0]

        @robust_async_api_call(RetryConfig(max_attempts=2, base_delay=0.1, timeout=1.0))
        async def async_api_function():
            call_count[0] += 1
            if call_count[0] == 1:
                raise httpx.NetworkError("Network error")
            return "success"

        result = await async_api_function()
        assert result == "success"
        assert call_count[0] == 2


class TestIntegrationScenarios:
    def test_httpx_client_integration(self):
        """Test integration with httpx client scenarios"""

        @retry_on_failure(NETWORK_API_CONFIG)
        def make_http_request(url: str):
            # Simulate different httpx error scenarios
            if "timeout" in url:
                raise httpx.TimeoutException("Request timeout")
            elif "network" in url:
                raise httpx.NetworkError("Network unreachable")
            elif "500" in url:
                response = Mock(status_code=500)
                raise httpx.HTTPStatusError("Internal server error", request=Mock(), response=response)
            elif "404" in url:
                response = Mock(status_code=404)
                raise httpx.HTTPStatusError("Not found", request=Mock(), response=response)
            return f"Success for {url}"

        # Should retry and eventually succeed
        assert make_http_request("http://example.com/success") == "Success for http://example.com/success"

        # Should not retry 404 errors
        with pytest.raises(httpx.HTTPStatusError):
            make_http_request("http://example.com/404")

    def test_openai_api_integration(self):
        """Test integration with OpenAI API error scenarios"""

        @retry_on_failure(RATE_LIMITED_API_CONFIG)
        def make_openai_request(prompt: str):
            if "rate_limit" in prompt:
                mock_response = Mock()
                mock_response.status_code = 429
                raise RateLimitError("Rate limited", response=mock_response, body=None)
            elif "server_error" in prompt:
                mock_request = Mock()
                error = APIError("Server error", request=mock_request, body=None)
                error.status_code = 500  # type: ignore[attr-defined]
                raise error
            elif "auth_error" in prompt:
                mock_request = Mock()
                error = APIError("Invalid API key", request=mock_request, body=None)
                error.status_code = 401  # type: ignore[attr-defined]
                raise error
            return f"Response for: {prompt}"

        # Should succeed immediately
        assert make_openai_request("Hello") == "Response for: Hello"

        # Should not retry auth errors
        with pytest.raises(APIError):
            make_openai_request("auth_error")

    @pytest.mark.asyncio
    async def test_concurrent_retry_behavior(self):
        """Test retry behavior under concurrent conditions"""
        call_counts = {"func1": 0, "func2": 0}

        @async_retry_on_failure(RetryConfig(max_attempts=2, base_delay=0.1))
        async def failing_function(name: str):
            call_counts[name] += 1
            if call_counts[name] == 1:
                raise httpx.NetworkError(f"Network error for {name}")
            return f"Success for {name}"

        # Run functions concurrently
        results = await asyncio.gather(
            failing_function("func1"),
            failing_function("func2"),
        )

        assert results == ["Success for func1", "Success for func2"]
        assert call_counts["func1"] == 2
        assert call_counts["func2"] == 2

    def test_configuration_based_retry_strategies(self):
        """Test different retry strategies based on configuration"""

        # Create fast test configurations to avoid long delays
        fast_config = RetryConfig(max_attempts=2, base_delay=0.01)
        medium_config = RetryConfig(max_attempts=3, base_delay=0.01)
        many_config = RetryConfig(max_attempts=5, base_delay=0.01)

        # Fast API configuration
        @retry_on_failure(fast_config)
        def fast_api_call():
            raise httpx.NetworkError("Network error")

        # Network API configuration
        @retry_on_failure(medium_config)
        def network_api_call():
            raise httpx.NetworkError("Network error")

        # Rate limited API configuration
        @retry_on_failure(many_config)
        def rate_limited_api_call():
            raise httpx.NetworkError("Network error")

        # Test that different configurations result in different retry attempts
        with pytest.raises(RetryError) as exc_info:
            fast_api_call()
        assert exc_info.value.attempts == 2

        with pytest.raises(RetryError) as exc_info:
            network_api_call()
        assert exc_info.value.attempts == 3

        with pytest.raises(RetryError) as exc_info:
            rate_limited_api_call()
        assert exc_info.value.attempts == 5


class TestEdgeCases:
    def test_zero_attempts_config(self):
        """Test behavior with zero max attempts"""

        @retry_on_failure(RetryConfig(max_attempts=0))
        def function_with_zero_attempts():
            return "success"

        # With 0 attempts, the range(0) will be empty, so the function should never run
        # This tests edge case handling - should raise RuntimeError
        with pytest.raises(RuntimeError, match="Unexpected retry logic error"):
            function_with_zero_attempts()

    def test_very_large_delay_config(self):
        """Test behavior with very large delay configuration"""
        # max_delay smaller than base, disable jitter
        config = RetryConfig(base_delay=1000.0, max_delay=1.0, jitter=False)

        # Should cap at max_delay
        delay = calculate_delay(0, config)
        assert delay == 1.0

    def test_negative_delay_components(self):
        """Test behavior with edge case delay configurations"""
        config = RetryConfig(base_delay=0.0, exponential_base=1.0)

        delay = calculate_delay(5, config)
        assert delay >= 0

    @pytest.mark.asyncio
    async def test_exception_preservation(self):
        """Test that original exception information is preserved"""
        original_error = httpx.NetworkError("Original network error")

        @async_retry_on_failure(RetryConfig(max_attempts=1, base_delay=0.1))
        async def failing_function():
            raise original_error

        with pytest.raises(RetryError) as exc_info:
            await failing_function()

        assert exc_info.value.original_error is original_error
        assert exc_info.value.attempts == 1
