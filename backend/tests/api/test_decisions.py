"""List, fetch, approve, and reject. Approval never rewrites the decision."""

from __future__ import annotations

import pytest
from app.models.domain import Decision
from fastapi.testclient import TestClient
from tests.api.support import ADMIN_HEADERS, build_client, make_record


def test_list_decisions_empty(client: TestClient) -> None:
    response = client.get("/decisions")

    assert response.status_code == 200
    assert response.json() == []


def test_list_decisions_filters_escalar() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record(id="dec_pay", invoice_id="INV-PAY", decision="PAGAR"))
    store.add_decision(make_record(id="dec_esc", invoice_id="INV-ESC", decision="ESCALAR"))
    store.add_decision(make_record(id="dec_stop", invoice_id="INV-STOP", decision="FRENAR"))

    response = client.get("/decisions", params={"decision": "ESCALAR"})

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == ["dec_esc"]


def test_list_decisions_keeps_insertion_order() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record(id="dec_b", invoice_id="INV-B", decision="FRENAR"))
    store.add_decision(make_record(id="dec_a", invoice_id="INV-A", decision="PAGAR"))

    response = client.get("/decisions")

    assert [item["id"] for item in response.json()] == ["dec_b", "dec_a"]


def test_list_decisions_rejects_unknown_value(client: TestClient) -> None:
    response = client.get("/decisions", params={"decision": "NOPE"})

    assert response.status_code == 422


def test_get_decision_missing_returns_404(client: TestClient) -> None:
    response = client.get("/decisions/missing")

    assert response.status_code == 404


def test_get_decision_uses_record_id_not_invoice_id() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record())

    by_invoice = client.get("/decisions/INV-0042")
    by_id = client.get("/decisions/dec_0042")

    assert by_invoice.status_code == 404
    assert by_id.status_code == 200
    assert by_id.json()["invoice_id"] == "INV-0042"


def test_approve_appends_event_and_keeps_decision() -> None:
    client, store, clock = build_client()
    record = make_record()
    store.add_decision(record)

    response = client.post(
        "/decisions/dec_0042/approve",
        json={"author": "cfo@demo.test", "reason": "Coincide con el presupuesto"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "ESCALAR"
    assert body["severity"] == 1
    assert record.human_events == []
    assert record.decision == "ESCALAR"
    updated = store.decisions[record.id]
    assert updated is not record
    assert updated.decision == "ESCALAR"
    assert updated.severity == 1
    assert len(updated.human_events) == 1
    event = updated.human_events[0]
    assert event.action == "aprobada_humano"
    assert event.author == "cfo@demo.test"
    assert event.reason == "Coincide con el presupuesto"
    assert event.at == clock.now
    assert body["human_events"][0]["action"] == "aprobada_humano"


def test_reject_appends_event_and_keeps_decision() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record())

    response = client.post(
        "/decisions/dec_0042/reject",
        json={"author": "cfo@demo.test", "reason": "Falta la orden de compra"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    updated = store.decisions["dec_0042"]
    assert updated.decision == "ESCALAR"
    assert updated.severity == 1
    assert updated.human_events[0].action == "rechazada_humano"


@pytest.mark.parametrize("decision", ["PAGAR", "FRENAR"])
def test_approve_non_escalar_returns_409_and_adds_no_event(decision: Decision) -> None:
    client, store, _clock = build_client()
    record = make_record(decision=decision)
    store.add_decision(record)

    response = client.post(
        f"/decisions/{record.id}/approve",
        json={"author": "cfo@demo.test", "reason": "No debería pasar"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 409
    assert store.decisions[record.id] is record
    assert store.decisions[record.id].human_events == []


def test_reject_empty_reason_returns_422() -> None:
    client, store, _clock = build_client()
    record = make_record()
    store.add_decision(record)

    response = client.post(
        "/decisions/dec_0042/reject",
        json={"author": "cfo@demo.test", "reason": ""},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422
    assert store.decisions[record.id] is record
    assert record.human_events == []


def test_approve_missing_author_returns_422() -> None:
    client, store, _clock = build_client()
    record = make_record()
    store.add_decision(record)

    response = client.post(
        "/decisions/dec_0042/approve",
        json={"reason": "Coincide con el presupuesto"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422
    assert record.human_events == []


def test_approve_extra_field_returns_422() -> None:
    client, store, _clock = build_client()
    record = make_record()
    store.add_decision(record)

    response = client.post(
        "/decisions/dec_0042/approve",
        json={
            "author": "cfo@demo.test",
            "reason": "Coincide con el presupuesto",
            "extra": 1,
        },
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422
    assert record.human_events == []


def test_approve_missing_decision_returns_404(client: TestClient) -> None:
    response = client.post(
        "/decisions/missing/approve",
        json={"author": "cfo@demo.test", "reason": "Coincide con el presupuesto"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 404
