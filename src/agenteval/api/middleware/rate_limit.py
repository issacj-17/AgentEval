"""
Rate Limiting Middleware for AgentEval API

Implements token bucket rate limiting with per-client tracking.
"""

import logging
import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket for rate limiting"""

    def __init__(self, rate: int, burst: int) -> None:
        """
        Initialize token bucket

        Args:
            rate: Tokens per minute
            burst: Maximum burst size
        """
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_update = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were available and consumed, False otherwise
        """
        now = time.time()
        elapsed = now - self.last_update

        # Refill tokens based on elapsed time
        # rate is per minute, so convert to per second
        tokens_to_add = elapsed * (self.rate / 60.0)
        self.tokens = min(self.burst, self.tokens + tokens_to_add)
        self.last_update = now

        # Try to consume tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        else:
            return False

    def get_wait_time(self) -> float:
        """
        Get estimated wait time until next token available

        Returns:
            Wait time in seconds
        """
        if self.tokens >= 1:
            return 0.0

        tokens_needed = 1 - self.tokens
        # rate is per minute, convert to per second
        seconds_per_token = 60.0 / self.rate
        return tokens_needed * seconds_per_token


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using token bucket algorithm

    Tracks clients by IP address and enforces per-client rate limits.
    """

    def __init__(self, app, requests_per_minute: int, burst: int) -> None:
        """
        Initialize rate limiter

        Args:
            app: FastAPI application
            requests_per_minute: Maximum requests per minute per client
            burst: Maximum burst size
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst = burst
        self.buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(requests_per_minute, burst)
        )
        logger.info(f"Rate limiting enabled: {requests_per_minute} req/min, burst {burst}")

    def _get_client_identifier(self, request: Request) -> str:
        """
        Get unique identifier for client

        Uses X-Forwarded-For if available, otherwise client IP.

        Args:
            request: FastAPI request

        Returns:
            Client identifier
        """
        # Check for forwarded IP (behind proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take first IP if multiple
            return forwarded_for.split(",")[0].strip()

        # Fallback to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response (either rate limited or from next handler)
        """
        # Skip rate limiting for health check endpoints
        if request.url.path.startswith("/api/v1/health"):
            return await call_next(request)

        # Get client identifier and bucket
        client_id = self._get_client_identifier(request)
        bucket = self.buckets[client_id]

        # Try to consume token
        if not bucket.consume():
            wait_time = bucket.get_wait_time()
            logger.warning(f"Rate limit exceeded for {client_id} on {request.url.path}")

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Too many requests. Please retry after {wait_time:.1f} seconds.",
                    "retry_after": int(wait_time) + 1,
                },
                headers={
                    "Retry-After": str(int(wait_time) + 1),
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to successful responses
        remaining_tokens = int(bucket.tokens)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining_tokens)

        return response
