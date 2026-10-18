"""T5.10 (D055) — GET /decisions/verify-chain: public, read-only, and
registered before `/decisions/{id}` so the literal path is not swallowed."""

from __future__ import annotations

from datetime import UTC, datetime

from app.api import create_app
from app.persistence import SqlStore, init_database
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from tests.api.support import TEST_ADMIN_KEY, load_approver_emails, load_rules, make_record


def test_verify_chain_is_ok_with_no_decisions_yet(client: TestClient) -> None:
    response = client.get("/decisions/verify-chain")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "length": 0, "first_broken_id": None}


def test_verify_chain_route_is_not_swallowed_by_decisions_id(client: TestClient) -> None:
    """If `/decisions/{id}` were registered first, this would 404 with
    "not_found" (id="verify-chain") instead of reaching the real handler."""
    response = client.get("/decisions/verify-chain")

    assert response.status_code == 200
    assert response.json() != {"detail": "not_found"}


def test_verify_chain_requires_no_admin_key(client: TestClient) -> None:
    """Public read-only endpoint (spec §2): no X-Admin-Key required, unlike
    PUT /rules and approve/reject."""
    response = client.get("/decisions/verify-chain")

    assert response.status_code == 200


def test_verify_chain_over_http_matches_sql_store_after_three_decisions(tmp_path) -> None:
    db_path = tmp_path / "blinka.sqlite"
    engine = create_engine(f"sqlite:///{db_path}")
    init_database(engine)
    store = SqlStore(engine)
    store.put_rules(load_rules())
    store.add_decision(make_record(id="dec_1", invoice_id="INV-1"))
    store.add_decision(make_record(id="dec_2", invoice_id="INV-2"))
    store.add_decision(make_record(id="dec_3", invoice_id="INV-3"))
    frozen = datetime(2026, 3, 4, 12, 0, tzinfo=UTC)
    app = create_app(
        store,
        lambda _u: make_record(),
        clock=lambda: frozen,
        rate_limit=1000,
        admin_api_key=TEST_ADMIN_KEY,
        approver_emails=load_approver_emails(),
    )
    http = TestClient(app)

    response = http.get("/decisions/verify-chain")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "length": 3, "first_broken_id": None}

    http.close()
    engine.dispose()


def test_verify_chain_over_http_reports_direct_db_tamper(tmp_path) -> None:
    from app.persistence.tables import DecisionRecordRow
    from sqlalchemy.orm import Session

    db_path = tmp_path / "blinka_tamper.sqlite"
    engine = create_engine(f"sqlite:///{db_path}")
    init_database(engine)
    store = SqlStore(engine)
    store.put_rules(load_rules())
    store.add_decision(make_record(id="dec_1", invoice_id="INV-1"))
    store.add_decision(make_record(id="dec_2", invoice_id="INV-2"))

    with Session(engine) as session:
        row = session.get(DecisionRecordRow, "dec_2")
        assert row is not None
        row.payload = row.payload.replace('"ESCALAR"', '"FRENAR"', 1)
        session.commit()

    frozen = datetime(2026, 3, 4, 12, 0, tzinfo=UTC)
    app = create_app(
        store,
        lambda _u: make_record(),
        clock=lambda: frozen,
        rate_limit=1000,
        admin_api_key=TEST_ADMIN_KEY,
        approver_emails=load_approver_emails(),
    )
    http = TestClient(app)

    response = http.get("/decisions/verify-chain")

    assert response.status_code == 200
    assert response.json() == {"ok": False, "length": 2, "first_broken_id": "dec_2"}

    http.close()
    engine.dispose()
