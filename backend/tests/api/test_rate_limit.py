"""Fixed window per client IP. Tests inject the limit; they do not read .env."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from tests.api.support import MutableClock, build_client


def test_over_limit_returns_429_with_retry_after() -> None:
    clock = MutableClock(datetime(2026, 3, 4, 12, 0, tzinfo=UTC))
    client, _store, _clock = build_client(rate_limit=2, clock=clock)

    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 200
    blocked = client.get("/openapi.json")

    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "rate_limited"}
    assert blocked.headers["retry-after"] == "60"


def test_limit_is_per_ip() -> None:
    clock = MutableClock(datetime(2026, 3, 4, 12, 0, tzinfo=UTC))
    client, _store, _clock = build_client(rate_limit=1, clock=clock)
    other = TestClient(client.app, client=("203.0.113.8", 9))

    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 429
    assert other.get("/health").status_code == 200


def test_window_resets_after_sixty_seconds() -> None:
    clock = MutableClock(datetime(2026, 3, 4, 12, 0, tzinfo=UTC))
    client, _store, _clock = build_client(rate_limit=1, clock=clock)

    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 429
    clock.now = clock.now + timedelta(seconds=60)

    assert client.get("/health").status_code == 200
