"""T9.1 (D061) — `/agreements/*` and `GET /rules/effective` HTTP contract.

§7 criterion 5: no key -> 401/503 before body validation; unknown
`confirmed_by` -> 422; stale `expected_version` -> 409; confirming twice ->
v1 superseded, v2 active; `verify-chain` ok and detects tampering with the
`agreement_change` entry.
"""

from __future__ import annotations

from app.api import create_app
from tests.api.support import ADMIN_HEADERS, build_client


class FakeAgreementLlm:
    def __init__(self, response: dict | None = None, *, error: Exception | None = None) -> None:
        self._response = response
        self._error = error
        self.calls: list[dict[str, str]] = []

    def complete_json(self, system: str, user: str) -> dict:
        self.calls.append({"system": system, "user": user})
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


_RETAINER_TERMS = {
    "kind": "retainer",
    "vendor_name": "Globex LLC",
    "currency": "USD",
    "periodicity": "monthly",
    "amount": {"min": 800, "max": 800},
    "valid_from": "2026-01-01",
    "valid_to": "2026-03-31",
}


def _confirm_body(**overrides: object) -> dict:
    body = {
        "terms": _RETAINER_TERMS,
        "confirmed_by": "cfo@demo.test",
        "expected_version": 0,
    }
    body.update(overrides)
    return body


# --- draft -------------------------------------------------------------------


def test_draft_without_key_returns_401_before_body_validation() -> None:
    client, _store, _clock = build_client()

    response = client.post("/agreements/draft", json={"bad": "body"})

    assert response.status_code == 401


def test_draft_without_configured_llm_is_empty_fail_closed() -> None:
    client, _store, _clock = build_client()

    response = client.post(
        "/agreements/draft", data={"text": "algún texto"}, headers=ADMIN_HEADERS
    )

    assert response.status_code == 200
    body = response.json()
    assert body["draft"] == {}
    assert "kind" not in body["draft"]
    assert body["source_sha256"]


def test_draft_with_fake_llm_returns_cited_fields() -> None:
    llm = FakeAgreementLlm(
        {
            "kind": "retainer",
            "vendor_name": "Globex LLC",
            "department": None,
            "currency": "USD",
            "valid_from": None,
            "valid_to": None,
            "periodicity": "monthly",
            "amount_min": 800,
            "amount_max": 800,
            "total_cap": None,
            "unit": None,
            "rate": None,
            "included_hours": None,
            "overtime_multiplier": None,
            "overtime_max_hours": None,
            "period_cap": None,
            "items": None,
            "tiers": None,
            "quotes": {
                "vendor_name": "Globex LLC es el beneficiario.",
                "currency": "800 USD mensuales.",
                "periodicity": "800 USD mensuales.",
                "amount_min": "800 USD mensuales.",
                "amount_max": "800 USD mensuales.",
            },
        }
    )
    from datetime import UTC, datetime

    from app.api.store import MemoryStore
    from fastapi.testclient import TestClient
    from tests.api.support import load_approver_emails, load_approver_groups, load_rules

    def default_processor(upload, owner_id):  # pragma: no cover - not exercised here
        raise AssertionError("not used")

    mem_store = MemoryStore(load_rules())
    app = create_app(
        mem_store,
        default_processor,
        clock=lambda: datetime(2026, 3, 4, 12, 0, tzinfo=UTC),
        rate_limit=1000,
        admin_api_key="test-admin-key",
        approver_emails=load_approver_emails(),
        approver_groups=load_approver_groups(),
        agreement_llm=llm,
    )
    client = TestClient(app, headers={"X-User-Id": "test-user-id"})

    response = client.post(
        "/agreements/draft",
        data={"text": "Globex LLC es el beneficiario. 800 USD mensuales."},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["draft"]["vendor_name"] == "Globex LLC"
    assert body["spans"]["vendor_name"]
    assert "vendor_name" not in body["missing"]


# --- confirm (PUT) -------------------------------------------------------------


def test_confirm_without_key_returns_401_before_body_validation() -> None:
    client, _store, _clock = build_client()

    response = client.put("/agreements/globex", json={"bad": "body"})

    assert response.status_code == 401


def test_confirm_unknown_approver_returns_422() -> None:
    client, _store, _clock = build_client()

    response = client.put(
        "/agreements/globex",
        json=_confirm_body(confirmed_by="nobody@demo.test"),
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "unknown_approver"


def test_confirm_creates_v1_and_appears_in_list_and_effective_rules() -> None:
    client, store, _clock = build_client()

    response = client.put(
        "/agreements/globex", json=_confirm_body(), headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 1
    assert body["status"] == "active"

    listed = client.get("/agreements").json()
    assert any(item["vendor_key"] == "globex" for item in listed)

    history = client.get("/agreements/globex").json()
    assert history["active"]["version"] == 1
    assert len(history["versions"]) == 1

    effective = client.get("/rules/effective").json()
    series = [s for s in effective["rules"]["payment_series"] if s["beneficiary"] == "Globex LLC"]
    assert len(series) == 1
    assert effective["provenance"]["payment_series:globex"] == "agr-globex-v1"


def test_stale_expected_version_returns_409() -> None:
    client, _store, _clock = build_client()
    client.put("/agreements/globex", json=_confirm_body(), headers=ADMIN_HEADERS)

    response = client.put(
        "/agreements/globex", json=_confirm_body(expected_version=0), headers=ADMIN_HEADERS
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "version_conflict"


def test_confirm_twice_supersedes_v1_and_activates_v2() -> None:
    client, _store, _clock = build_client()
    client.put("/agreements/globex", json=_confirm_body(), headers=ADMIN_HEADERS)

    response = client.put(
        "/agreements/globex", json=_confirm_body(expected_version=1), headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    assert response.json()["version"] == 2

    history = client.get("/agreements/globex").json()
    statuses = {v["version"]: v["status"] for v in history["versions"]}
    assert statuses == {1: "superseded", 2: "active"}


def test_confirm_conflicting_with_hand_written_series_returns_409() -> None:
    from app.models.rules_config import AmountRange, PaymentSeries, RulesConfig

    client, store, _clock = build_client()
    manual_series = PaymentSeries(
        id="manual-globex",
        beneficiary="Globex LLC",
        periodicity="monthly",
        currency="USD",
        expected_amount=AmountRange(min=800, max=800),
        start="2026-01-01",
    )
    hand_written = store.rules.model_copy(update={"payment_series": [manual_series]})
    store.put_rules(RulesConfig.model_validate(hand_written.model_dump(mode="json")))

    response = client.put("/agreements/globex", json=_confirm_body(), headers=ADMIN_HEADERS)

    assert response.status_code == 409
    assert response.json()["detail"] == "agreement_conflicts_with_rules"


def test_vendor_key_mismatch_returns_422() -> None:
    client, _store, _clock = build_client()

    response = client.put(
        "/agreements/not-globex", json=_confirm_body(), headers=ADMIN_HEADERS
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "vendor_key_mismatch"


def test_invalid_terms_body_returns_422() -> None:
    client, _store, _clock = build_client()
    bad = _confirm_body()
    bad["terms"] = {"kind": "retainer"}  # missing required fields

    response = client.put("/agreements/globex", json=bad, headers=ADMIN_HEADERS)

    assert response.status_code == 422


# --- deactivate ----------------------------------------------------------------


def test_deactivate_unknown_vendor_returns_404() -> None:
    client, _store, _clock = build_client()

    response = client.post(
        "/agreements/globex/deactivate",
        json={"author": "cfo@demo.test"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 404


def test_deactivate_known_vendor_marks_inactive() -> None:
    client, _store, _clock = build_client()
    client.put("/agreements/globex", json=_confirm_body(), headers=ADMIN_HEADERS)

    response = client.post(
        "/agreements/globex/deactivate",
        json={"author": "cfo@demo.test"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"

    effective = client.get("/rules/effective").json()
    series = [s for s in effective["rules"]["payment_series"] if s["beneficiary"] == "Globex LLC"]
    assert series == []


# --- GET /agreements/{vendor_key} 404 -----------------------------------------


def test_get_unknown_agreement_returns_404() -> None:
    client, _store, _clock = build_client()

    response = client.get("/agreements/does-not-exist")

    assert response.status_code == 404


# --- verify-chain --------------------------------------------------------------


def test_verify_chain_ok_after_confirm_and_detects_tamper() -> None:
    client, store, _clock = build_client()
    client.put("/agreements/globex", json=_confirm_body(), headers=ADMIN_HEADERS)

    assert client.get("/decisions/verify-chain").json()["ok"] is True

    # Direct in-memory tamper of the agreement_change entry's payload.
    entry = store._chain[-1]  # noqa: SLF001
    tampered = dict(entry.payload)
    tampered["status"] = "inactive"
    object.__setattr__(entry, "payload", tampered)

    result = client.get("/decisions/verify-chain").json()
    assert result["ok"] is False


# --- Product requirement (coordinator, 2026-10-18): a draft alone never adds
# a vendor or mutates rules; only a confirmed PUT does, and the vendor's
# first invoice still escalates on R20 (same audited pattern as T7.4).


def test_draft_alone_never_adds_vendor_or_mutates_rules() -> None:
    client, store, _clock = build_client()
    before = store.rules.model_dump(mode="json")

    client.post(
        "/agreements/draft",
        data={"text": "Brand New Vendor LLC. 800 USD mensuales."},
        headers=ADMIN_HEADERS,
    )

    assert store.rules.model_dump(mode="json") == before
    assert "Brand New Vendor LLC" not in store.rules.allowed_beneficiaries
    assert store.list_agreement_vendor_keys() == []


def test_confirm_adds_new_vendor_immediately_but_first_invoice_still_escalates() -> None:
    client, store, _clock = build_client()
    new_vendor_terms = {
        "kind": "retainer",
        "vendor_name": "Brand New Vendor LLC",
        "currency": "USD",
        "periodicity": "monthly",
        "amount": {"min": 500, "max": 500},
        "valid_from": "2026-01-01",
    }

    response = client.put(
        "/agreements/brand%20new%20vendor",
        json={"terms": new_vendor_terms, "confirmed_by": "cfo@demo.test", "expected_version": 0},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200

    # Confirmed: the vendor is on the *effective* (compiled) allowlist
    # immediately -- `store.rules` itself (the hand-written base) is never
    # mutated; `compile_rules` is the one source of truth the motor/graph use.
    effective = client.get("/rules/effective").json()
    assert "Brand New Vendor LLC" in effective["rules"]["allowed_beneficiaries"]
    assert effective["rules"]["vendor_onboarding"]["enabled"] is True

    # But R20 still fires for its first invoice: never an automatic PAGAR.
    from app.models.domain import SEVERITY
    from app.models.rules_config import RulesConfig
    from app.rules.decide import decide
    from app.rules.fx import load_fx_table
    from app.rules.run_checks import run_deterministic_checks
    from tests.api.support import REPO_ROOT
    from tests.rules.test_rules_r01_r13 import make_context

    fx_table = load_fx_table(REPO_ROOT / "data" / "fx.json")
    compiled_rules = RulesConfig.model_validate(effective["rules"])
    ctx = make_context(
        compiled_rules,
        fx_table,
        beneficiary="Brand New Vendor LLC",
        amount=500,
        amount_base=500.0,
        due_date="2026-02-01",
    )
    checks = run_deterministic_checks(ctx)
    r20 = next(c for c in checks if c.rule == "R20")
    assert r20.result == "FALLA"
    decision = decide(checks)
    assert decision != "PAGAR"
    assert SEVERITY[decision] >= SEVERITY["ESCALAR"]
