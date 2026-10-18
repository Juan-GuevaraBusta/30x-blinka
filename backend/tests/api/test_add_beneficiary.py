"""T7.4 — POST /decisions/{id}/add-beneficiary (audited allowlist, allowlist_change chain)."""

from __future__ import annotations

import copy

from app.models.domain import DecisionRecord
from app.models.rules_config import VendorOnboarding
from tests.api.support import ADMIN_HEADERS, build_client, make_record


def _payload(
    author: str = "finanzas@demo.test",
    reason: str = "Proveedor conocido",
) -> dict[str, str]:
    return {"author": author, "reason": reason}


def _r01_frenar_record(
    *,
    beneficiary: str = "Nuevo Vendor SAS",
    decision_id: str = "dec_r01",
) -> DecisionRecord:
    checks = [
        {
            "rule": "R01",
            "name": "Beneficiario permitido",
            "result": "FALLA",
            "detail": f"{beneficiary} no está en la lista.",
            "on_fail": "FRENAR",
        }
    ]
    record = make_record(id=decision_id, invoice_id="INV-R01", decision="FRENAR", checks=checks)
    extracted = record.extracted.model_copy(update={"beneficiary": beneficiary})
    return record.model_copy(update={"extracted": extracted, "severity": 2})


def _enable_onboarding(store) -> None:
    rules = store.rules.model_copy(
        update={"vendor_onboarding": VendorOnboarding(enabled=True), "vendor_additions": []}
    )
    store.put_rules(rules)


def test_add_beneficiary_without_key_returns_401_before_body_validation() -> None:
    client, store, _clock = build_client()
    store.add_decision(_r01_frenar_record())
    _enable_onboarding(store)

    response = client.post("/decisions/dec_r01/add-beneficiary", json={"bad": "body"})

    assert response.status_code == 401
    assert response.json() == {"detail": "missing_admin_key"}


def test_add_beneficiary_unknown_author_returns_422() -> None:
    client, store, _clock = build_client()
    store.add_decision(_r01_frenar_record())
    _enable_onboarding(store)

    response = client.post(
        "/decisions/dec_r01/add-beneficiary",
        json=_payload(author="nobody@example.com"),
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "unknown_approver"}


def test_add_beneficiary_when_r01_ok_returns_409() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record(decision="ESCALAR"))
    _enable_onboarding(store)

    response = client.post(
        "/decisions/dec_0042/add-beneficiary",
        json=_payload(),
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "r01_not_failed"}


def test_add_beneficiary_disabled_returns_403() -> None:
    client, store, _clock = build_client()
    store.add_decision(_r01_frenar_record())

    response = client.post(
        "/decisions/dec_r01/add-beneficiary",
        json=_payload(),
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "vendor_onboarding_disabled"}


def test_add_beneficiary_success_updates_rules_and_chain() -> None:
    client, store, _clock = build_client()
    before = _r01_frenar_record()
    store.add_decision(before)
    chain_before = copy.deepcopy(store._chain)
    record_before = copy.deepcopy(store.decisions["dec_r01"])
    _enable_onboarding(store)

    response = client.post(
        "/decisions/dec_r01/add-beneficiary",
        json=_payload(),
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert "Nuevo Vendor SAS" in body["allowed_beneficiaries"]
    assert len(body["vendor_additions"]) == 1
    assert body["vendor_additions"][0]["source_decision_id"] == "dec_r01"

    assert store.decisions["dec_r01"] == record_before
    assert store._chain[: len(chain_before)] == chain_before
    assert store._chain[-1].kind == "allowlist_change"
    assert store._chain[-1].ref_id == "dec_r01"

    verify = client.get("/decisions/verify-chain")
    assert verify.json()["ok"] is True


def test_tampered_allowlist_change_breaks_chain() -> None:
    client, store, _clock = build_client()
    store.add_decision(_r01_frenar_record())
    _enable_onboarding(store)
    client.post(
        "/decisions/dec_r01/add-beneficiary",
        json=_payload(),
        headers=ADMIN_HEADERS,
    )
    entry = store._chain[-1]
    assert entry.payload is not None
    tampered = {**entry.payload, "reason": "alterado"}
    store._chain[-1] = type(entry)(
        kind=entry.kind,
        ref_id=entry.ref_id,
        payload=tampered,
        prev_hash=entry.prev_hash,
        record_hash=entry.record_hash,
    )
    result = client.get("/decisions/verify-chain").json()
    assert result["ok"] is False
    assert result["first_broken_id"] == "dec_r01"
