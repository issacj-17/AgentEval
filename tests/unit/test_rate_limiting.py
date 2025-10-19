"""
Unit tests for Rate Limiting Middleware

Tests token bucket algorithm and rate limiting enforcement.
"""

import time
from unittest.mock import MagicMock

import pytest
from fastapi import Request
from fastapi import status as http_status

from agenteval.api.middleware.rate_limit import RateLimitMiddleware, TokenBucket


class TestTokenBucket:
    """Test TokenBucket algorithm"""

    def test_token_bucket_initialization(self):
        """Test token bucket initializes with burst capacity"""
        bucket = TokenBucket(rate=60, burst=10)

        assert bucket.rate == 60
        assert bucket.burst == 10
        assert bucket.tokens == 10.0  # Starts full

    def test_consume_tokens_when_available(self):
        """Test consuming tokens when available"""
        bucket = TokenBucket(rate=60, burst=10)

        # Should succeed
        assert bucket.consume(1) is True
        assert bucket.tokens < 10.0  # Should be approximately 9

        # Should succeed again
        assert bucket.consume(1) is True
        assert bucket.tokens < 9.0  # Should be approximately 8

    def test_consume_tokens_when_insufficient(self):
        """Test consuming tokens when insufficient"""
        bucket = TokenBucket(rate=60, burst=2)

        # Consume all tokens
        assert bucket.consume(1) is True
        assert bucket.consume(1) is True

        # Should fail - no tokens left
        assert bucket.consume(1) is False
        assert bucket.tokens < 0.01  # Approximately 0 (allowing for float precision)

    def test_tokens_refill_over_time(self):
        """Test that tokens refill based on rate"""
        bucket = TokenBucket(rate=60, burst=10)  # 60 per minute = 1 per second

        # Consume all tokens
        for _ in range(10):
            bucket.consume(1)
        assert bucket.tokens < 0.01  # Approximately 0

        # Wait 1 second
        time.sleep(1.1)

        # Should have ~1 token refilled
        assert bucket.consume(1) is True

    def test_tokens_dont_exceed_burst(self):
        """Test that tokens don't exceed burst capacity"""
        bucket = TokenBucket(rate=60, burst=5)

        # Start with full bucket
        assert bucket.tokens == 5.0

        # Wait for refill time
        time.sleep(2.0)

        # Try to consume - should still be capped at burst
        consumed = 0
        while bucket.consume(1):
            consumed += 1

        # Should not exceed burst capacity
        assert consumed <= 5

    def test_get_wait_time_when_tokens_available(self):
        """Test wait time when tokens are available"""
        bucket = TokenBucket(rate=60, burst=10)

        wait_time = bucket.get_wait_time()
        assert wait_time == 0.0

    def test_get_wait_time_when_no_tokens(self):
        """Test wait time when no tokens available"""
        bucket = TokenBucket(rate=60, burst=1)

        # Consume all tokens
        bucket.consume(1)

        wait_time = bucket.get_wait_time()
        assert wait_time > 0.0
        assert wait_time <= 1.1  # Should be around 1 second for 60/min rate

    def test_multiple_token_consumption(self):
        """Test consuming multiple tokens at once"""
        bucket = TokenBucket(rate=60, burst=10)

        # Consume 5 tokens
        assert bucket.consume(5) is True
        assert bucket.tokens == 5.0

        # Try to consume 10 - should fail
        assert bucket.consume(10) is False


class TestRateLimitMiddleware:
    """Test RateLimitMiddleware"""

    @pytest.fixture
    def middleware(self):
        """Create rate limit middleware instance"""
        app = MagicMock()
        return RateLimitMiddleware(app=app, requests_per_minute=60, burst=10)

    @pytest.fixture
    def mock_request(self):
        """Create mock FastAPI request"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/test"
        request.headers.get.return_value = None
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        return request

    def test_middleware_initializes_with_configuration(self, middleware):
        """Test middleware initializes with configuration"""
        assert middleware.requests_per_minute == 60
        assert middleware.burst == 10
        assert isinstance(middleware.buckets, dict)

    def test_get_client_identifier_from_direct_ip(self, middleware, mock_request):
        """Test extracting client identifier from direct IP"""
        mock_request.client.host = "192.168.1.1"

        client_id = middleware._get_client_identifier(mock_request)
        assert client_id == "192.168.1.1"

    def test_get_client_identifier_from_forwarded_header(self, middleware, mock_request):
        """Test extracting client identifier from X-Forwarded-For"""
        mock_request.headers.get.return_value = "203.0.113.1, 192.168.1.1"

        client_id = middleware._get_client_identifier(mock_request)
        assert client_id == "203.0.113.1"

    def test_get_client_identifier_handles_missing_client(self, middleware):
        """Test handling missing client info"""
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = None
        mock_request.client = None

        client_id = middleware._get_client_identifier(mock_request)
        assert client_id == "unknown"

    @pytest.mark.asyncio
    async def test_dispatch_allows_request_when_tokens_available(self, middleware, mock_request):
        """Test that requests are allowed when tokens are available"""

        # Mock the next handler
        async def call_next(request):
            response = MagicMock()
            response.headers = {}
            return response

        response = await middleware.dispatch(mock_request, call_next)

        # Should not be rate limited
        assert response.headers["X-RateLimit-Limit"] == "60"
        assert int(response.headers["X-RateLimit-Remaining"]) >= 0

    @pytest.mark.asyncio
    async def test_dispatch_blocks_request_when_rate_exceeded(self, middleware, mock_request):
        """Test that requests are blocked when rate limit exceeded"""
        # Consume all tokens for this client
        client_id = middleware._get_client_identifier(mock_request)
        bucket = middleware.buckets[client_id]

        for _ in range(10):  # Burst size
            bucket.consume(1)

        # Mock the next handler
        async def call_next(request):
            response = MagicMock()
            response.headers = {}
            return response

        response = await middleware.dispatch(mock_request, call_next)

        # Should be rate limited
        assert response.status_code == http_status.HTTP_429_TOO_MANY_REQUESTS
        assert "Retry-After" in response.headers

    @pytest.mark.asyncio
    async def test_dispatch_exempts_health_check_endpoints(self, middleware):
        """Test that health check endpoints are exempt from rate limiting"""
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/health"
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        # Mock the next handler
        async def call_next(request):
            response = MagicMock()
            response.headers = {}
            return response

        # Even with exhausted bucket, health check should pass
        client_id = middleware._get_client_identifier(mock_request)
        bucket = middleware.buckets[client_id]
        for _ in range(10):
            bucket.consume(1)

        response = await middleware.dispatch(mock_request, call_next)

        # Should not be rate limited (health check exempt)
        assert (
            not hasattr(response, "status_code")
            or response.status_code != http_status.HTTP_429_TOO_MANY_REQUESTS
        )

    @pytest.mark.asyncio
    async def test_rate_limit_headers_in_response(self, middleware, mock_request):
        """Test that rate limit headers are added to responses"""

        async def call_next(request):
            response = MagicMock()
            response.headers = {}
            return response

        response = await middleware.dispatch(mock_request, call_next)

        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    @pytest.mark.asyncio
    async def test_different_clients_have_separate_buckets(self, middleware):
        """Test that different clients have separate rate limit buckets"""
        # Create two different clients
        request1 = MagicMock(spec=Request)
        request1.url.path = "/api/v1/test"
        request1.headers.get.return_value = None
        request1.client = MagicMock()
        request1.client.host = "192.168.1.1"

        request2 = MagicMock(spec=Request)
        request2.url.path = "/api/v1/test"
        request2.headers.get.return_value = None
        request2.client = MagicMock()
        request2.client.host = "192.168.1.2"

        async def call_next(request):
            response = MagicMock()
            response.headers = {}
            return response

        # Exhaust client1's bucket
        for _ in range(10):
            await middleware.dispatch(request1, call_next)

        # Client2 should still have tokens
        response = await middleware.dispatch(request2, call_next)
        assert "X-RateLimit-Remaining" in response.headers
        remaining = int(response.headers["X-RateLimit-Remaining"])
        assert remaining > 0  # Client2 should have tokens
