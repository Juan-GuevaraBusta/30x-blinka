"""Production ASGI factory (T4.9): SQLite boot, URL rewrite, CORS guard. No sockets."""

from __future__ import annotations

import pytest
from app.api.asgi import (
    InvalidCorsOriginsError,
    create_production_app,
    prepare_database_url,
)
from app.persistence import SqlStore, seed_rules
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from tests.api.support import ADMIN_HEADERS, RULES_PATH, TEST_ADMIN_KEY


def test_postgresql_scheme_rewritten_without_connecting() -> None:
    url = prepare_database_url("postgresql://demo.example/blinka")

    assert url.startswith("postgresql+psycopg://")
    assert "demo.example" in url
    assert "sslmode=require" in url


def test_render_internal_host_skips_sslmode() -> None:
    url = prepare_database_url("postgresql://user:pass@dpg-abc123-a/blinka")

    assert url.startswith("postgresql+psycopg://")
    assert "sslmode" not in url


def test_factory_sqlite_seed_get_put(tmp_path) -> None:
    db = tmp_path / "boot.sqlite"
    mapping = {"DATABASE_URL": f"sqlite:///{db}", "ADMIN_API_KEY": TEST_ADMIN_KEY}
    app = create_production_app(mapping, rules_path=RULES_PATH, cors_origins="")
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    got = client.get("/rules")
    assert got.status_code == 200
    body = got.json()
    assert body["human_approval_threshold"] == 3000.0

    updated = {**body, "human_approval_threshold": 2500.0}
    put = client.put("/rules", json=updated, headers=ADMIN_HEADERS)
    assert put.status_code == 200
    assert put.json()["human_approval_threshold"] == 2500.0

    again = client.get("/rules")
    assert again.json()["human_approval_threshold"] == 2500.0


def test_second_seed_does_not_overwrite_put(tmp_path) -> None:
    db = tmp_path / "boot.sqlite"
    mapping = {"DATABASE_URL": f"sqlite:///{db}", "ADMIN_API_KEY": TEST_ADMIN_KEY}
    app = create_production_app(mapping, rules_path=RULES_PATH, cors_origins="")
    client = TestClient(app)
    base = client.get("/rules").json()
    custom = {**base, "human_approval_threshold": 2500.0}
    client.put("/rules", json=custom, headers=ADMIN_HEADERS)

    store = SqlStore(create_engine(mapping["DATABASE_URL"]))
    seeded_again = seed_rules(store, RULES_PATH)

    assert seeded_again.human_approval_threshold == 2500.0
    assert client.get("/rules").json()["human_approval_threshold"] == 2500.0


def test_put_rules_returns_503_when_admin_api_key_env_unset(tmp_path) -> None:
    """T5.9 (D055): fail-closed when the production env never set ADMIN_API_KEY."""
    db = tmp_path / "boot.sqlite"
    mapping = {"DATABASE_URL": f"sqlite:///{db}"}
    app = create_production_app(mapping, rules_path=RULES_PATH, cors_origins="")
    client = TestClient(app)

    response = client.put(
        "/rules", json=client.get("/rules").json(), headers=ADMIN_HEADERS
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "admin_key_not_configured"}


def test_decisions_empty_after_seed(tmp_path) -> None:
    db = tmp_path / "boot.sqlite"
    mapping = {"DATABASE_URL": f"sqlite:///{db}"}
    app = create_production_app(mapping, rules_path=RULES_PATH, cors_origins="")
    client = TestClient(app)

    assert client.get("/decisions").json() == []


def test_star_cors_aborts_startup(tmp_path) -> None:
    db = tmp_path / "boot.sqlite"
    mapping = {"DATABASE_URL": f"sqlite:///{db}", "CORS_ORIGINS": "*"}

    with pytest.raises(InvalidCorsOriginsError):
        create_production_app(mapping, rules_path=RULES_PATH)


def test_import_app_api_does_not_open_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    def _forbidden_create_engine(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("create_engine must not run on import app.api")

    monkeypatch.setattr("sqlalchemy.create_engine", _forbidden_create_engine)
    import importlib
    import sys

    sys.modules.pop("app.api", None)
    import app.api

    importlib.reload(app.api)
    assert app.api.__all__ == ["create_app"]
