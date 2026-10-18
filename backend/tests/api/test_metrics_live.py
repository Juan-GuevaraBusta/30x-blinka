"""GET /metrics/live — company-scoped operation counters from stored decisions only.

Never reads `eval/reports/` (I9 spirit for the live section: computed only from
what `store` already holds). Company scoping mirrors `GET /decisions`.
"""

from __future__ import annotations

from app.api.tenancy import DEMO_COMPANY_ID
from tests.api.support import TEST_USER_ID, attach_test_user, build_client, make_record


def test_empty_company_has_zero_everything_and_null_pct() -> None:
    client, _store, _clock = build_client()

    response = client.get("/metrics/live")

    assert response.status_code == 200
    assert response.json() == {
        "total": 0,
        "pagar": 0,
        "frenar": 0,
        "escalar": 0,
        "auto_decided_pct": None,
        "pending_approvals": 0,
        "approved_by_humans": 0,
    }


def test_counts_decisions_and_pending_and_approved() -> None:
    client, store, _clock = build_client()
    store.add_decision(make_record(id="dec_pagar", invoice_id="INV-1", decision="PAGAR"))
    store.add_decision(make_record(id="dec_frenar", invoice_id="INV-2", decision="FRENAR"))
    store.add_decision(
        make_record(id="dec_escalar_pending", invoice_id="INV-3", decision="ESCALAR")
    )
    store.add_decision(
        make_record(
            id="dec_escalar_approved",
            invoice_id="INV-4",
            decision="ESCALAR",
            human_events=[
                {
                    "author": "finanzas@demo.test",
                    "at": "2026-03-04T12:00:00Z",
                    "action": "aprobada_humano",
                    "reason": "ok",
                }
            ],
        )
    )
    store.add_decision(
        make_record(
            id="dec_escalar_rejected",
            invoice_id="INV-5",
            decision="ESCALAR",
            human_events=[
                {
                    "author": "finanzas@demo.test",
                    "at": "2026-03-04T12:00:00Z",
                    "action": "rechazada_humano",
                    "reason": "no",
                }
            ],
        )
    )

    response = client.get("/metrics/live")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert body["pagar"] == 1
    assert body["frenar"] == 1
    assert body["escalar"] == 3
    assert body["auto_decided_pct"] == (1 + 1) / 5 * 100
    # Only the ESCALAR with zero human_events is pending.
    assert body["pending_approvals"] == 1
    # Only the one with an `aprobada_humano` event counts as approved.
    assert body["approved_by_humans"] == 1


def test_isolates_counts_per_company() -> None:
    client, store, _clock = build_client()
    other_user = "other-company-user"
    other_company = store.create_company(
        name="Other Co",
        base_currency="USD",
        is_demo=False,
        created_by=other_user,
        at="2026-03-04T12:00:00+00:00",
    )
    attach_test_user(
        store, user_id=other_user, email="other@other.test", company_id=other_company.id
    )
    store.add_decision(
        make_record(id="dec_mine", invoice_id="INV-MINE", decision="PAGAR"),
        owner_id=TEST_USER_ID,
        company_id=DEMO_COMPANY_ID,
    )
    store.add_decision(
        make_record(id="dec_theirs", invoice_id="INV-THEIRS", decision="FRENAR"),
        owner_id=other_user,
        company_id=other_company.id,
    )

    response = client.get("/metrics/live")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["pagar"] == 1
    assert body["frenar"] == 0
