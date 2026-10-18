"""T5.10 (D055) — MemoryStore append-only hash chain mirrors SqlStore's
semantics so GET /decisions/verify-chain works the same regardless of
backend."""

from __future__ import annotations

from datetime import UTC, datetime

from app.api.store import MemoryStore
from app.models.domain import HumanEvent
from tests.api.support import load_rules, make_record


def _store() -> MemoryStore:
    return MemoryStore(load_rules())


def _approve(store: MemoryStore, decision_id: str) -> None:
    store.add_human_event(
        decision_id,
        HumanEvent(
            author="cfo@demo.test",
            at=datetime(2026, 3, 4, 12, 0, tzinfo=UTC),
            action="aprobada_humano",
            reason="Coincide con el presupuesto",
        ),
    )


def test_three_inserted_decisions_chain_from_genesis() -> None:
    store = _store()
    store.add_decision(make_record(id="dec_1", invoice_id="INV-1"))
    store.add_decision(make_record(id="dec_2", invoice_id="INV-2"))
    store.add_decision(make_record(id="dec_3", invoice_id="INV-3"))

    result = store.verify_chain()
    assert result.ok is True
    assert result.length == 3
    assert result.first_broken_id is None


def test_approve_after_three_decisions_appends_a_fourth_entry_chain_still_ok() -> None:
    store = _store()
    store.add_decision(make_record(id="dec_1", invoice_id="INV-1"))
    store.add_decision(make_record(id="dec_2", invoice_id="INV-2"))
    store.add_decision(make_record(id="dec_3", invoice_id="INV-3"))

    _approve(store, "dec_1")

    assert len(store._chain) == 4
    assert store._chain[3].kind == "human_event"
    assert store._chain[3].ref_id == "dec_1"

    result = store.verify_chain()
    assert result.ok is True
    assert result.length == 4


def test_approve_never_rewrites_any_existing_chain_entry() -> None:
    store = _store()
    store.add_decision(make_record(id="dec_1", invoice_id="INV-1"))
    store.add_decision(make_record(id="dec_2", invoice_id="INV-2"))
    store.add_decision(make_record(id="dec_3", invoice_id="INV-3"))

    before = list(store._chain)

    _approve(store, "dec_1")

    after = store._chain
    assert after[: len(before)] == before
    assert len(after) == len(before) + 1


def test_verify_chain_detects_a_decision_tampered_directly_on_the_store() -> None:
    store = _store()
    store.add_decision(make_record(id="dec_1", invoice_id="INV-1"))
    store.add_decision(make_record(id="dec_2", invoice_id="INV-2"))

    # Direct mutation bypassing add_decision/add_human_event, like editing a
    # row through a raw Session for SqlStore.
    tampered = store.decisions["dec_2"].model_copy(update={"summary": "Alterado."})
    store.decisions["dec_2"] = tampered

    result = store.verify_chain()

    assert result.ok is False
    assert result.first_broken_id == "dec_2"


def test_verify_chain_detects_a_human_event_tampered_directly_on_the_store() -> None:
    store = _store()
    store.add_decision(make_record(id="dec_1", invoice_id="INV-1"))
    _approve(store, "dec_1")

    event_entry = store._chain[1]
    assert event_entry.kind == "human_event"
    assert event_entry.payload is not None
    tampered_payload = {**event_entry.payload, "reason": "Motivo alterado"}
    store._chain[1] = type(event_entry)(
        kind=event_entry.kind,
        ref_id=event_entry.ref_id,
        payload=tampered_payload,
        prev_hash=event_entry.prev_hash,
        record_hash=event_entry.record_hash,
    )

    result = store.verify_chain()

    assert result.ok is False
    assert result.first_broken_id == "dec_1"


def test_verify_chain_detects_a_deleted_entry() -> None:
    store = _store()
    store.add_decision(make_record(id="dec_1", invoice_id="INV-1"))
    store.add_decision(make_record(id="dec_2", invoice_id="INV-2"))
    store.add_decision(make_record(id="dec_3", invoice_id="INV-3"))

    del store._chain[1]

    result = store.verify_chain()

    assert result.ok is False
    assert result.first_broken_id == "dec_3"


def test_approve_on_an_earlier_decision_does_not_disturb_later_decisions() -> None:
    store = _store()
    store.add_decision(make_record(id="dec_1", invoice_id="INV-1"))
    store.add_decision(make_record(id="dec_2", invoice_id="INV-2"))
    store.add_decision(make_record(id="dec_3", invoice_id="INV-3"))

    before = list(store._chain)

    _approve(store, "dec_1")

    after = store._chain
    assert after[:3] == before
    assert len(after) == 4

    result = store.verify_chain()
    assert result.ok is True
    assert result.length == 4
