"""
Lightweight in-process rate limiting middleware.
"""

import asyncio
import time
from collections import defaultdict, deque
from collections.abc import Iterable

from fastapi import Request
from starlette import status as http_status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple sliding-window rate limiter for FastAPI/Starlette applications.

    This implementation is intentionally minimal and keeps per-identifier
    request timestamps in memory. It is suitable for single-process usage.
    """

    def __init__(
        self,
        app,
        max_per_minute: int,
        burst: int,
        exempt_paths: Iterable[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.max_per_minute = max_per_minute
        self.burst = max(burst, max_per_minute) if burst < max_per_minute else burst
        self.exempt_paths: set[str] = set(exempt_paths or [])
        self._lock = asyncio.Lock()
        self._requests: defaultdict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path in self.exempt_paths:
            return await call_next(request)

        identifier = request.headers.get("X-Forwarded-For")
        if not identifier:
            client = request.client
            identifier = client.host if client else "unknown"

        now = time.monotonic()

        async with self._lock:
            bucket = self._requests[identifier]

            # Drop expired requests (older than 60 seconds)
            while bucket and now - bucket[0] > 60:
                bucket.popleft()

            if len(bucket) >= self.burst or len(bucket) >= self.max_per_minute:
                return JSONResponse(
                    {"detail": "Rate limit exceeded"},
                    status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={"Retry-After": "60"},
                )

            bucket.append(now)

        response = await call_next(request)

        # Opportunistic cleanup if the bucket became empty
        if not self._requests[identifier]:
            self._requests.pop(identifier, None)

        return response
