"""SqlStore round-trip, ordering, restart, and HTTP with SQLite on tmp_path."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from app.api import create_app
from app.api.store import DuplicateDecisionError
from app.models.domain import HumanEvent
from app.models.rules_config import RulesConfig
from app.persistence import RulesMissing, SqlStore, init_database
from app.persistence.tables import DecisionRecordRow
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from tests.api.support import load_rules, make_record, rules_payload


def _engine_for(tmp_path) -> object:
    url = f"sqlite:///{tmp_path}/blinka.sqlite"
    engine = create_engine(url)
    init_database(engine)
    return engine


def test_rules_missing_without_seed(tmp_path) -> None:
    store = SqlStore(_engine_for(tmp_path))

    with pytest.raises(RulesMissing):
        _ = store.rules


def test_decision_round_trip(tmp_path) -> None:
    engine = _engine_for(tmp_path)
    store = SqlStore(engine)
    store.put_rules(load_rules())
    record = make_record()
    before = record.model_dump(mode="json")

    store.add_decision(record)
    loaded = store.get(record.id)

    assert loaded is not None
    assert loaded is not record
    assert loaded.model_dump(mode="json") == before


def test_duplicate_invoice_raises_and_leaves_one_row(tmp_path) -> None:
    engine = _engine_for(tmp_path)
    store = SqlStore(engine)
    store.put_rules(load_rules())
    store.add_decision(make_record())

    with pytest.raises(DuplicateDecisionError):
        store.add_decision(make_record(id="dec_other", invoice_id="INV-0042"))

    with Session(engine) as session:
        count = session.scalar(select(func.count()).select_from(DecisionRecordRow))
        assert count == 1


def test_decisions_keep_insertion_order(tmp_path) -> None:
    store = SqlStore(_engine_for(tmp_path))
    store.put_rules(load_rules())
    store.add_decision(make_record(id="dec_b", invoice_id="INV-B", decision="FRENAR"))
    store.add_decision(make_record(id="dec_a", invoice_id="INV-A", decision="PAGAR"))

    assert list(store.decisions) == ["dec_b", "dec_a"]


def test_add_human_event_does_not_mutate_caller_object(tmp_path) -> None:
    store = SqlStore(_engine_for(tmp_path))
    store.put_rules(load_rules())
    original = make_record()
    store.add_decision(original)
    event = HumanEvent(
        author="cfo@demo.test",
        at=datetime(2026, 3, 4, 12, 0, tzinfo=UTC),
        action="aprobada_humano",
        reason="OK",
    )

    updated = store.add_human_event(original.id, event)

    assert original.human_events == []
    assert original.decision == "ESCALAR"
    assert updated.decision == "ESCALAR"
    assert updated.severity == original.severity
    assert len(updated.human_events) == 1
    reloaded = store.get(original.id)
    assert reloaded is not None
    assert reloaded.model_dump(mode="json") == updated.model_dump(mode="json")


def test_put_rules_does_not_change_saved_decision_payload(tmp_path) -> None:
    engine = _engine_for(tmp_path)
    store = SqlStore(engine)
    store.put_rules(load_rules())
    record = make_record()
    store.add_decision(record)
    before_payload = store.get(record.id).model_dump(mode="json")

    custom = RulesConfig.model_validate({**rules_payload(), "human_approval_threshold": 2500.0})
    store.put_rules(custom)

    after_payload = store.get(record.id).model_dump(mode="json")
    assert after_payload == before_payload
    assert store.rules.human_approval_threshold == 2500.0


def test_survives_engine_dispose_and_reopen(tmp_path) -> None:
    db_path = tmp_path / "blinka.sqlite"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    init_database(engine)
    store = SqlStore(engine)
    store.put_rules(load_rules())
    record = make_record()
    store.add_decision(record)
    expected = record.model_dump(mode="json")
    engine.dispose()

    engine2 = create_engine(url)
    store2 = SqlStore(engine2)
    loaded = store2.get(record.id)

    assert loaded is not None
    assert loaded is not record
    assert loaded.model_dump(mode="json") == expected
    engine2.dispose()


def test_invalid_payload_raises_on_read(tmp_path) -> None:
    engine = _engine_for(tmp_path)
    store = SqlStore(engine)
    store.put_rules(load_rules())
    with Session(engine) as session:
        session.add(
            DecisionRecordRow(
                id="bad",
                invoice_id="INV-BAD",
                decision="PAGAR",
                position=1,
                payload='{"id":"bad","extra":1}',
            )
        )
        session.commit()

    with pytest.raises(ValidationError):
        store.get("bad")


def test_http_sql_store_rules_survive_restart(tmp_path) -> None:
    db_path = tmp_path / "blinka.sqlite"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    init_database(engine)
    store = SqlStore(engine)
    store.put_rules(load_rules())
    frozen = datetime(2026, 3, 4, 12, 0, tzinfo=UTC)
    app = create_app(store, lambda _u: make_record(), clock=lambda: frozen, rate_limit=1000)
    client = TestClient(app)

    custom = RulesConfig.model_validate({**rules_payload(), "human_approval_threshold": 2500.0})
    assert client.put("/rules", json=json.loads(custom.model_dump_json())).status_code == 200

    esc = make_record()
    store.add_decision(esc)
    approve = client.post(
        "/decisions/dec_0042/approve",
        json={"author": "cfo@demo.test", "reason": "Coincide con el presupuesto"},
    )
    assert approve.status_code == 200
    assert approve.json()["decision"] == "ESCALAR"

    client.close()
    engine.dispose()

    engine2 = create_engine(url)
    store2 = SqlStore(engine2)
    app2 = create_app(store2, lambda _u: make_record(), clock=lambda: frozen, rate_limit=1000)
    client2 = TestClient(app2)

    rules_body = client2.get("/rules").json()
    assert rules_body["human_approval_threshold"] == 2500.0

    reloaded = store2.get("dec_0042")
    assert reloaded is not None
    assert reloaded.decision == "ESCALAR"
    assert len(reloaded.human_events) == 1

    pagar = make_record(id="dec_pay", invoice_id="INV-PAY", decision="PAGAR")
    store2.add_decision(pagar)
    conflict = client2.post(
        "/decisions/dec_pay/approve",
        json={"author": "cfo@demo.test", "reason": "No debería pasar"},
    )
    assert conflict.status_code == 409
    assert store2.get("dec_pay").human_events == []

    client2.close()
    engine2.dispose()
