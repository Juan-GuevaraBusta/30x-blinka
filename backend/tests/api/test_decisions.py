"""List, fetch, approve, and reject. Approval never rewrites the decision."""

from __future__ import annotations

import pytest
from app.models.domain import Decision
from fastapi.testclient import TestClient
from tests.api.support import (
    ADMIN_HEADERS,
    USER_HEADERS,
    attach_test_user,
    build_client,
    make_record,
)


def test_list_decisions_empty(client: TestClient) -> None:
    response = client.get("/decisions")

    assert response.status_code == 200
    assert response.json() == []


def test_list_decisions_requires_user_header() -> None:
    client, _store, _clock = build_client()
    bare = TestClient(client.app)
    response = bare.get("/decisions")
    assert response.status_code == 401
    assert response.json()["detail"] == "missing_user_id"


def test_list_decisions_isolated_by_company() -> None:
    """T9.8 (D067): decisions are scoped by the caller's company, not by uploader."""
    client, store, _clock = build_client()
    other = store.create_company(
        name="Otra SA", base_currency="USD", is_demo=False, created_by="owner-b", at="t"
    )
    attach_test_user(store, user_id="owner-a", email="a@demo.test")
    attach_test_user(store, user_id="owner-b", email="b@otra.test", company_id=other.id)
    store.add_decision(make_record(id="dec_a", invoice_id="INV-A"), owner_id="owner-a")
    store.add_decision(
        make_record(id="dec_b", invoice_id="INV-B"), owner_id="owner-b", company_id=other.id
    )

    as_a = client.get("/decisions", headers={**USER_HEADERS, "X-User-Id": "owner-a"})
    as_b = client.get("/decisions", headers={**USER_HEADERS, "X-User-Id": "owner-b"})

    assert [item["id"] for item in as_a.json()] == ["dec_a"]
    assert [item["id"] for item in as_b.json()] == ["dec_b"]


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


# P0 safety fix: a human must not be able to approve a decision whose invoice
# (same normalized beneficiary + invoice number, both default to "Globex LLC"
# / "GX-2231" in `make_record`) is an exact duplicate of one already settled
# (PAGAR, or an ESCALAR decision that already has an `aprobada_humano`
# event -- `decision` stays "ESCALAR" forever per I2).
def test_approve_duplicate_of_paid_decision_returns_409_and_adds_no_event() -> None:
    client, store, _clock = build_client()
    paid = make_record(id="dec_paid", invoice_id="INV-PAID", decision="PAGAR")
    pending = make_record(id="dec_dup", invoice_id="INV-DUP")
    store.add_decision(paid)
    store.add_decision(pending)

    response = client.post(
        "/decisions/dec_dup/approve",
        json={"author": "cfo@demo.test", "reason": "No debería pasar"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "duplicate_of_settled"
    assert store.decisions["dec_dup"] is pending
    assert store.decisions["dec_dup"].human_events == []


def test_approve_duplicate_of_already_approved_decision_returns_409() -> None:
    client, store, _clock = build_client()
    approved = make_record(
        id="dec_approved",
        invoice_id="INV-APPROVED",
        human_events=[
            {
                "author": "cfo@demo.test",
                "at": "2026-03-04T10:00:00Z",
                "action": "aprobada_humano",
                "reason": "Primera aprobación.",
            }
        ],
    )
    dup = make_record(id="dec_dup2", invoice_id="INV-DUP2")
    store.add_decision(approved)
    store.add_decision(dup)

    response = client.post(
        "/decisions/dec_dup2/approve",
        json={"author": "cfo@demo.test", "reason": "No debería pasar"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "duplicate_of_settled"
    assert store.decisions["dec_dup2"].human_events == []


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
