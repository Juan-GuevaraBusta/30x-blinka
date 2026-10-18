"""T5.10 (D055) — boot-time backfill of `chain_entries` for `decision_record`
rows that predate the hash chain entirely (a live deploy's existing
Postgres table, simulated here with a hand-built legacy SQLite table that
has no `chain_entries` table at all).

`create_all` already creates `chain_entries` on any database (new or
pre-existing) since the table itself is new, but it cannot populate it for
rows that existed before it did. `ensure_decision_chain_backfilled` (called
from `init_database`) does that once, idempotently, in `position` order.
"""

from __future__ import annotations

from app.persistence import SqlStore, init_database
from app.persistence.tables import ChainEntryRow
from app.records.chain import GENESIS_PREV_HASH, compute_decision_entry_hash
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from tests.api.support import make_record


def _make_legacy_decision_record_table(engine) -> None:
    """A `decision_record` table exactly as T4.2 created it, with no
    `chain_entries` table at all -- a database from before T5.10."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE decision_record (
                    id VARCHAR PRIMARY KEY,
                    invoice_id VARCHAR UNIQUE NOT NULL,
                    decision VARCHAR NOT NULL,
                    position INTEGER NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
        )


def _insert_legacy_row(engine, *, position: int, record) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO decision_record (id, invoice_id, decision, position, payload)
                VALUES (:id, :invoice_id, :decision, :position, :payload)
                """
            ),
            {
                "id": record.id,
                "invoice_id": record.invoice_id,
                "decision": record.decision,
                "position": position,
                "payload": record.model_dump_json(),
            },
        )


def test_boot_backfill_appends_one_decision_entry_per_legacy_row_in_position_order(
    tmp_path,
) -> None:
    db_path = tmp_path / "legacy.sqlite"
    engine = create_engine(f"sqlite:///{db_path}")
    _make_legacy_decision_record_table(engine)
    rec_1 = make_record(id="dec_old_1", invoice_id="INV-OLD-1")
    rec_2 = make_record(id="dec_old_2", invoice_id="INV-OLD-2")
    _insert_legacy_row(engine, position=1, record=rec_1)
    _insert_legacy_row(engine, position=2, record=rec_2)

    init_database(engine)  # boots like `create_production_app` would

    with Session(engine) as session:
        entries = session.scalars(select(ChainEntryRow).order_by(ChainEntryRow.seq)).all()

    expected_hash_1 = compute_decision_entry_hash(rec_1, GENESIS_PREV_HASH)
    expected_hash_2 = compute_decision_entry_hash(rec_2, expected_hash_1)
    assert [(e.kind, e.ref_id, e.prev_hash, e.record_hash) for e in entries] == [
        ("decision", "dec_old_1", GENESIS_PREV_HASH, expected_hash_1),
        ("decision", "dec_old_2", expected_hash_1, expected_hash_2),
    ]

    store = SqlStore(engine)
    result = store.verify_chain()
    assert result.ok is True
    assert result.length == 2


def test_boot_backfill_is_idempotent_and_never_rewrites_an_existing_entry(tmp_path) -> None:
    db_path = tmp_path / "legacy_idempotent.sqlite"
    engine = create_engine(f"sqlite:///{db_path}")
    _make_legacy_decision_record_table(engine)
    _insert_legacy_row(engine, position=1, record=make_record(id="dec_old_1", invoice_id="I-1"))

    init_database(engine)

    with Session(engine) as session:
        before = [
            (e.seq, e.kind, e.ref_id, e.prev_hash, e.record_hash)
            for e in session.scalars(select(ChainEntryRow)).all()
        ]

    # A legacy row plus a fresh one added through the normal store path.
    store = SqlStore(engine)
    store.add_decision(make_record(id="dec_new_1", invoice_id="I-NEW-1"))

    init_database(engine)  # a second boot must not touch what is already there

    with Session(engine) as session:
        after = [
            (e.seq, e.kind, e.ref_id, e.prev_hash, e.record_hash)
            for e in session.scalars(select(ChainEntryRow)).all()
        ]

    assert after[: len(before)] == before
    assert len(after) == len(before) + 1

    result = store.verify_chain()
    assert result.ok is True
    assert result.length == 2


def test_new_database_never_needs_the_legacy_backfill_path(tmp_path) -> None:
    """A brand-new database gets `chain_entries` from `create_all` directly;
    the backfill finds no pre-existing rows and stays a no-op."""
    db_path = tmp_path / "fresh.sqlite"
    engine = create_engine(f"sqlite:///{db_path}")
    init_database(engine)

    with Session(engine) as session:
        entries = session.scalars(select(ChainEntryRow)).all()
    assert entries == []

    store = SqlStore(engine)
    store.add_decision(make_record(id="dec_1", invoice_id="INV-1"))
    result = store.verify_chain()
    assert result.ok is True
    assert result.length == 1
