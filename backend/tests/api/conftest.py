"""Fixtures for the T4.1 HTTP contract."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from tests.api.support import build_client


@pytest.fixture
def client() -> TestClient:
    http, _store, _clock = build_client()
    return http
