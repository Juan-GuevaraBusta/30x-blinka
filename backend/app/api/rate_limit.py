"""Fixed one-minute window per client IP. In-process dict; no Redis and no user id."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class FixedWindowLimiter:
    def __init__(
        self,
        limit: int,
        clock: Callable[[], datetime],
        *,
        window_seconds: int = 60,
    ) -> None:
        if limit < 1:
            raise ValueError("rate limit must be >= 1")
        self.limit = limit
        self.clock = clock
        self.window_seconds = window_seconds
        self._windows: dict[str, tuple[int, int]] = {}

    def allow(self, key: str) -> bool:
        bucket = int(self.clock().timestamp()) // self.window_seconds
        current = self._windows.get(key)
        if current is None or current[0] != bucket:
            self._windows[key] = (bucket, 1)
            return True
        count = current[1]
        if count >= self.limit:
            return False
        self._windows[key] = (bucket, count + 1)
        return True


class RateLimitMiddleware:
    """Own ASGI wrapper. A rejected call gets 429 and does not reach the route."""

    def __init__(self, app: ASGIApp, limiter: FixedWindowLimiter) -> None:
        self.app = app
        self.limiter = limiter

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        client = scope.get("client")
        host = client[0] if client else "unknown"
        if self.limiter.allow(host):
            await self.app(scope, receive, send)
            return
        response = JSONResponse(
            {"detail": "rate_limited"},
            status_code=429,
            headers={"Retry-After": "60"},
        )
        await response(scope, receive, send)
