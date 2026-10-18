"""PUT /rules: invalid bodies stay 422 and do not replace the stored rules."""

from __future__ import annotations

from app.models.domain import DecisionRecord
from fastapi.testclient import TestClient
from tests.api.support import ADMIN_HEADERS, build_client, make_record, rules_payload


def test_put_rules_negative_per_payment_returns_422_and_keeps_previous(
    client: TestClient,
) -> None:
    before = client.get("/rules").json()
    payload = rules_payload()
    limits = payload["limits"]
    assert isinstance(limits, dict)
    limits["per_payment"] = -1

    response = client.put("/rules", json=payload, headers=ADMIN_HEADERS)

    assert response.status_code == 422
    assert client.get("/rules").json() == before


def test_put_rules_missing_per_payment_returns_422(client: TestClient) -> None:
    before = client.get("/rules").json()
    payload = rules_payload()
    limits = payload["limits"]
    assert isinstance(limits, dict)
    del limits["per_payment"]

    response = client.put("/rules", json=payload, headers=ADMIN_HEADERS)

    assert response.status_code == 422
    assert client.get("/rules").json() == before


def test_put_rules_unknown_field_returns_422(client: TestClient) -> None:
    before = client.get("/rules").json()
    payload = rules_payload()
    payload["extra_field"] = 1

    response = client.put("/rules", json=payload, headers=ADMIN_HEADERS)

    assert response.status_code == 422
    assert client.get("/rules").json() == before


def test_put_rules_valid_threshold_is_returned_by_next_get(client: TestClient) -> None:
    payload = rules_payload()
    payload["human_approval_threshold"] = 2500

    response = client.put("/rules", json=payload, headers=ADMIN_HEADERS)

    assert response.status_code == 200
    assert response.json()["human_approval_threshold"] == 2500
    assert client.get("/rules").json()["human_approval_threshold"] == 2500


def test_put_rules_does_not_change_stored_decisions() -> None:
    client, store, _clock = build_client()
    record = make_record()
    store.add_decision(record)
    before = record.model_dump(mode="json")
    payload = rules_payload()
    payload["human_approval_threshold"] = 2500

    response = client.put("/rules", json=payload, headers=ADMIN_HEADERS)

    assert response.status_code == 200
    kept: DecisionRecord = store.decisions[record.id]
    assert kept.model_dump(mode="json") == before
    assert kept is record
