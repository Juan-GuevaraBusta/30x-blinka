"""T5.10 (D055) — SqlStore append-only hash chain: happy path, direct-DB
tamper of a decision and of a human event, deletion, and the "never rewrite
a stored hash" property that motivated this design.

These mutate rows directly via `Session`/raw SQL, never through
`store.add_decision`/`store.add_human_event`/the HTTP API, to prove
`SqlStore.verify_chain` detects edits that bypass the API.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.domain import HumanEvent
from app.persistence import SqlStore, init_database
from app.persistence.tables import ChainEntryRow, DecisionRecordRow
from app.records.chain import GENESIS_PREV_HASH
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session
from tests.api.support import load_rules, make_record


def _engine_for(tmp_path) -> object:
    url = f"sqlite:///{tmp_path}/blinka_chain.sqlite"
    engine = create_engine(url)
    init_database(engine)
    return engine


def _chain_rows(engine) -> list[ChainEntryRow]:
    with Session(engine) as session:
        return list(session.scalars(select(ChainEntryRow).order_by(ChainEntryRow.seq)).all())


def _chain_snapshot(engine) -> list[tuple[int, str, str, str | None, str, str]]:
    """Field-value snapshot (not ORM identity) so two reads taken at
    different times can be compared with `==`."""
    return [
        (row.seq, row.kind, row.ref_id, row.payload, row.prev_hash, row.record_hash)
        for row in _chain_rows(engine)
    ]


def _approve(store: SqlStore, decision_id: str) -> None:
    store.add_human_event(
        decision_id,
        HumanEvent(
            author="cfo@demo.test",
            at=datetime(2026, 3, 4, 12, 0, tzinfo=UTC),
            action="aprobada_humano",
            reason="Coincide con el presupuesto",
        ),
    )


def test_three_inserted_decisions_chain_from_genesis(tmp_path) -> None:
    engine = _engine_for(tmp_path)
    store = SqlStore(engine)
    store.put_rules(load_rules())
    store.add_decision(make_record(id="dec_1", invoice_id="INV-1"))
    store.add_decision(make_record(id="dec_2", invoice_id="INV-2"))
    store.add_decision(make_record(id="dec_3", invoice_id="INV-3"))

    rows = _chain_rows(engine)
    assert [row.kind for row in rows] == ["decision", "decision", "decision"]
    assert [row.ref_id for row in rows] == ["dec_1", "dec_2", "dec_3"]
    assert rows[0].prev_hash == GENESIS_PREV_HASH
    assert rows[1].prev_hash == rows[0].record_hash
    assert rows[2].prev_hash == rows[1].record_hash

    result = store.verify_chain()

    assert result.ok is True
    assert result.length == 3
    assert result.first_broken_id is None


def test_approve_after_three_decisions_appends_a_fourth_entry_chain_still_ok(tmp_path) -> None:
    engine = _engine_for(tmp_path)
    store = SqlStore(engine)
    store.put_rules(load_rules())
    store.add_decision(make_record(id="dec_1", invoice_id="INV-1"))
    store.add_decision(make_record(id="dec_2", invoice_id="INV-2"))
    store.add_decision(make_record(id="dec_3", invoice_id="INV-3"))

    _approve(store, "dec_1")

    rows = _chain_rows(engine)
    assert len(rows) == 4
    assert rows[3].kind == "human_event"
    assert rows[3].ref_id == "dec_1"
    assert rows[3].prev_hash == rows[2].record_hash  # chains from the current tip

    result = store.verify_chain()
    assert result.ok is True
    assert result.length == 4


def test_approve_never_rewrites_any_existing_chain_entry(tmp_path) -> None:
    """The exact property this design is for: appending a human event must
    not UPDATE a single byte of an entry that was already there."""
    engine = _engine_for(tmp_path)
    store = SqlStore(engine)
    store.put_rules(load_rules())
    store.add_decision(make_record(id="dec_1", invoice_id="INV-1"))
    store.add_decision(make_record(id="dec_2", invoice_id="INV-2"))
    store.add_decision(make_record(id="dec_3", invoice_id="INV-3"))

    before = _chain_snapshot(engine)

    _approve(store, "dec_1")  # dec_1 is the earliest row -- the worst case for a rewrite bug

    after = _chain_snapshot(engine)

    assert after[: len(before)] == before  # every pre-existing entry is byte-for-byte untouched
    assert len(after) == len(before) + 1  # exactly one new entry was appended


def test_verify_chain_detects_a_decision_payload_tampered_directly_in_the_database(
    tmp_path,
) -> None:
    engine = _engine_for(tmp_path)
    store = SqlStore(engine)
    store.put_rules(load_rules())
    store.add_decision(make_record(id="dec_1", invoice_id="INV-1"))
    store.add_decision(make_record(id="dec_2", invoice_id="INV-2"))
    store.add_decision(make_record(id="dec_3", invoice_id="INV-3"))

    # Direct DB edit, not via the API/store: change the second decision's
    # payload without touching its chain entry.
    with Session(engine) as session:
        row = session.get(DecisionRecordRow, "dec_2")
        assert row is not None
        row.payload = row.payload.replace('"ESCALAR"', '"FRENAR"', 1)
        session.commit()

    result = store.verify_chain()

    assert result.ok is False
    assert result.first_broken_id == "dec_2"
    assert result.length == 3


def test_verify_chain_detects_a_human_event_tampered_directly_in_the_database(tmp_path) -> None:
    engine = _engine_for(tmp_path)
    store = SqlStore(engine)
    store.put_rules(load_rules())
    store.add_decision(make_record(id="dec_1", invoice_id="INV-1"))
    _approve(store, "dec_1")

    with Session(engine) as session:
        event_row = session.scalars(
            select(ChainEntryRow).where(ChainEntryRow.kind == "human_event")
        ).one()
        assert event_row.payload is not None
        event_row.payload = event_row.payload.replace(
            "Coincide con el presupuesto", "Motivo alterado", 1
        )
        session.commit()

    result = store.verify_chain()

    assert result.ok is False
    assert result.first_broken_id == "dec_1"
    assert result.length == 2


def test_verify_chain_detects_a_deleted_entry(tmp_path) -> None:
    engine = _engine_for(tmp_path)
    store = SqlStore(engine)
    store.put_rules(load_rules())
    store.add_decision(make_record(id="dec_1", invoice_id="INV-1"))
    store.add_decision(make_record(id="dec_2", invoice_id="INV-2"))
    store.add_decision(make_record(id="dec_3", invoice_id="INV-3"))

    with Session(engine) as session:
        middle = session.scalars(
            select(ChainEntryRow).where(ChainEntryRow.ref_id == "dec_2")
        ).one()
        session.execute(delete(ChainEntryRow).where(ChainEntryRow.seq == middle.seq))
        session.commit()

    result = store.verify_chain()

    assert result.ok is False
    assert result.first_broken_id == "dec_3"
    assert result.length == 2


def test_approve_on_an_earlier_decision_does_not_disturb_later_decisions(tmp_path) -> None:
    """A human event on dec_1, appended *after* dec_2 and dec_3 already
    exist, must not require (or trigger) any change to dec_2/dec_3's
    entries -- unlike the earlier cascading-rehash design this replaces."""
    engine = _engine_for(tmp_path)
    store = SqlStore(engine)
    store.put_rules(load_rules())
    store.add_decision(make_record(id="dec_1", invoice_id="INV-1"))
    store.add_decision(make_record(id="dec_2", invoice_id="INV-2"))
    store.add_decision(make_record(id="dec_3", invoice_id="INV-3"))

    before = _chain_snapshot(engine)

    _approve(store, "dec_1")

    after = _chain_snapshot(engine)

    assert after[:3] == before
    assert len(after) == 4
    assert after[3][1] == "human_event"
    assert after[3][2] == "dec_1"

    result = store.verify_chain()
    assert result.ok is True
    assert result.length == 4
