"""Health, metrics nulls, and the committed OpenAPI document."""

from __future__ import annotations

import json

from app.api.schemas import MetricsReading
from fastapi.testclient import TestClient
from tests.api.support import REPO_ROOT, build_client

_CONTRACT_PATHS = (
    "/rules",
    "/decisions",
    "/decisions/{id}",
    "/invoices",
    "/decisions/{id}/approve",
    "/decisions/{id}/reject",
    "/decisions/{id}/approval",
    "/metrics",
    "/health",
    "/openapi.json",
)


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metrics_without_report_are_null(client: TestClient) -> None:
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.json() == {
        "unsafe_pay": None,
        "autonomy_pct": None,
        "source": "none",
    }


def test_metrics_reader_numbers_pass_through() -> None:
    def reader() -> MetricsReading:
        return MetricsReading(unsafe_pay=2, autonomy_pct=15.5)

    client, _store, _clock = build_client(metrics_reader=reader)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.json() == {
        "unsafe_pay": 2,
        "autonomy_pct": 15.5,
        "source": "report",
    }


def test_openapi_lists_contract_paths(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    document = response.json()
    assert document["openapi"].startswith("3.")
    assert document["info"]["title"] == "blinka-invoice-agent"
    paths = document["paths"]
    for path in _CONTRACT_PATHS:
        assert path in paths
    assert "get" in paths["/rules"]
    assert "put" in paths["/rules"]
    assert "get" in paths["/decisions"]
    assert "get" in paths["/decisions/{id}"]
    assert "post" in paths["/invoices"]
    assert "post" in paths["/decisions/{id}/approve"]
    assert "post" in paths["/decisions/{id}/reject"]
    assert "get" in paths["/decisions/{id}/approval"]
    assert "get" in paths["/metrics"]
    assert "get" in paths["/health"]
    assert "get" in paths["/openapi.json"]


def test_committed_openapi_paths_match_app(client: TestClient) -> None:
    live = client.get("/openapi.json").json()
    committed = json.loads(
        (REPO_ROOT / "backend" / "openapi.json").read_text(encoding="utf-8")
    )

    assert committed["info"]["title"] == "blinka-invoice-agent"
    assert committed["paths"] == live["paths"]
