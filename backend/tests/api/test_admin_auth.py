"""T5.9 (D055): X-Admin-Key on mutating endpoints and approve/reject author allowlist."""

from __future__ import annotations

import hmac

import pytest
from tests.api.support import (
    ADMIN_HEADERS,
    build_client,
    load_approver_emails,
    make_record,
    rules_payload,
)


def _approve_payload() -> dict[str, str]:
    return {"author": "cfo@demo.test", "reason": "Coincide con el presupuesto"}


# --- ADMIN_API_KEY not configured: fail-closed 503 ---------------------------------


def test_put_rules_returns_503_when_admin_key_not_configured() -> None:
    client, _store, _clock = build_client(admin_api_key=None)
    before = client.get("/rules").json()

    response = client.put("/rules", json=rules_payload(), headers=ADMIN_HEADERS)

    assert response.status_code == 503
    assert response.json() == {"detail": "admin_key_not_configured"}
    assert client.get("/rules").json() == before


def test_approve_returns_503_when_admin_key_not_configured() -> None:
    client, store, _clock = build_client(admin_api_key=None)
    record = make_record()
    store.add_decision(record)

    response = client.post(
        "/decisions/dec_0042/approve", json=_approve_payload(), headers=ADMIN_HEADERS
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "admin_key_not_configured"}
    assert store.decisions["dec_0042"].human_events == []


def test_reject_returns_503_when_admin_key_not_configured() -> None:
    client, store, _clock = build_client(admin_api_key=None)
    record = make_record()
    store.add_decision(record)

    response = client.post(
        "/decisions/dec_0042/reject", json=_approve_payload(), headers=ADMIN_HEADERS
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "admin_key_not_configured"}
    assert store.decisions["dec_0042"].human_events == []


# --- ADMIN_API_KEY configured: missing/wrong header -> 401 -------------------------


def test_put_rules_without_header_returns_401_missing() -> None:
    client, _store, _clock = build_client()

    response = client.put("/rules", json=rules_payload())

    assert response.status_code == 401
    assert response.json() == {"detail": "missing_admin_key"}


def test_put_rules_with_wrong_header_returns_401_invalid() -> None:
    client, _store, _clock = build_client()

    response = client.put(
        "/rules", json=rules_payload(), headers={"X-Admin-Key": "nope"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_admin_key"}


def test_approve_without_header_returns_401_missing() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record())

    response = client.post("/decisions/dec_0042/approve", json=_approve_payload())

    assert response.status_code == 401
    assert response.json() == {"detail": "missing_admin_key"}
    assert store.decisions["dec_0042"].human_events == []


def test_reject_with_wrong_header_returns_401_invalid() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record())

    response = client.post(
        "/decisions/dec_0042/reject",
        json=_approve_payload(),
        headers={"X-Admin-Key": "nope"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_admin_key"}
    assert store.decisions["dec_0042"].human_events == []


# --- correct key: happy path --------------------------------------------------------


def test_put_rules_with_correct_header_returns_200() -> None:
    client, _store, _clock = build_client()

    response = client.put("/rules", json=rules_payload(), headers=ADMIN_HEADERS)

    assert response.status_code == 200


# --- author must be one of data/company.json's approvers values --------------------


def test_approve_unknown_author_returns_422_and_adds_no_event() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record())

    response = client.post(
        "/decisions/dec_0042/approve",
        json={"author": "intruder@example.com", "reason": "no autorizado"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "unknown_approver"}
    assert store.decisions["dec_0042"].human_events == []


def test_reject_unknown_author_returns_422_and_adds_no_event() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record())

    response = client.post(
        "/decisions/dec_0042/reject",
        json={"author": "intruder@example.com", "reason": "no autorizado"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "unknown_approver"}
    assert store.decisions["dec_0042"].human_events == []


def test_approve_with_known_approver_and_correct_key_returns_200() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record())
    approvers = load_approver_emails()
    assert "finanzas@demo.test" in approvers

    response = client.post(
        "/decisions/dec_0042/approve",
        json={"author": "finanzas@demo.test", "reason": "Coincide con el presupuesto"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    assert store.decisions["dec_0042"].human_events[0].author == "finanzas@demo.test"


# --- GET endpoints and POST /invoices stay public -----------------------------------


@pytest.mark.parametrize(
    "path",
    ["/rules", "/decisions", "/metrics", "/health"],
)
def test_get_endpoints_stay_public_without_header(path: str) -> None:
    client, _store, _clock = build_client()

    response = client.get(path)

    assert response.status_code == 200


# --- constant-time comparison is actually used --------------------------------------


# --- R3: auth runs BEFORE body validation (401/503 before 422) --------------------


def test_put_rules_with_invalid_body_and_no_key_returns_401_not_422() -> None:
    """Follow-up to T5.9 review: an unauthenticated caller must never learn body
    shape via 422 before the admin-key check runs."""
    client, _store, _clock = build_client()

    response = client.put("/rules", json={"not": "a rules document"})

    assert response.status_code == 401
    assert response.json() == {"detail": "missing_admin_key"}


def test_put_rules_with_invalid_body_and_unset_key_returns_503() -> None:
    client, _store, _clock = build_client(admin_api_key=None)

    response = client.put("/rules", json={"not": "a rules document"})

    assert response.status_code == 503
    assert response.json() == {"detail": "admin_key_not_configured"}


def test_approve_with_invalid_body_and_no_key_returns_401_not_422() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record())

    response = client.post("/decisions/dec_0042/approve", json={"not": "valid"})

    assert response.status_code == 401
    assert response.json() == {"detail": "missing_admin_key"}
    assert store.decisions["dec_0042"].human_events == []


def test_reject_with_invalid_body_and_no_key_returns_401_not_422() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record())

    response = client.post("/decisions/dec_0042/reject", json={"not": "valid"})

    assert response.status_code == 401
    assert response.json() == {"detail": "missing_admin_key"}
    assert store.decisions["dec_0042"].human_events == []


def test_admin_key_comparison_uses_compare_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[bytes, bytes]] = []
    real_compare_digest = hmac.compare_digest

    def spy(a: bytes, b: bytes) -> bool:
        calls.append((a, b))
        return real_compare_digest(a, b)

    monkeypatch.setattr("app.api.app.hmac.compare_digest", spy)
    client, _store, _clock = build_client()

    response = client.put("/rules", json=rules_payload(), headers=ADMIN_HEADERS)

    assert response.status_code == 200
    assert len(calls) == 1
