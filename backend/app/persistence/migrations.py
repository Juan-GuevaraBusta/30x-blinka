"""Boot-time, no-Alembic backfill for the T5.10 (D055) append-only chain.

`chain_entries` is a brand-new table (`app.persistence.tables.ChainEntryRow`),
so `metadata.create_all` (called by `init_database` before this module runs)
already creates it on any database, new or pre-existing -- `create_all` only
ever creates tables that do not exist yet, and never alters one that does, so
a `decision_record` table from before T5.10 is untouched (it still has no
`prev_hash`/`record_hash` columns; those live in `chain_entries` now, not on
`decision_record`, specifically so nothing on that row is ever rewritten --
see `app.records.chain`'s module docstring).

What `create_all` cannot do is *populate* `chain_entries` for
`decision_record` rows that existed before this table did. This module does
exactly that, once, idempotently: it appends one `decision` chain entry per
pre-existing row that does not already have one, in `position` order,
continuing from the current chain tip (or genesis if the chain is empty).
Every append here goes through the same `compute_decision_entry_hash` as
`SqlStore.add_decision`, and never rewrites an entry that already exists.

Documented limitation: a human event recorded on a pre-existing row *before*
this code existed (embedded in that row's `payload.human_events`, from a
deploy that predates T5.10) has no corresponding `human_event` chain entry,
and this backfill does not invent one retroactively -- there is no reliable
timestamp/ordering to place it at. Only its decision gets backfilled.
"""

from __future__ import annotations

from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.domain import DecisionRecord
from app.records.chain import GENESIS_PREV_HASH, compute_decision_entry_hash


def ensure_decision_chain_backfilled(engine: Engine) -> None:
    """Idempotent: append a `decision` chain entry for every
    `DecisionRecordRow` that does not have one yet, in `position` order.

    No-op on a fresh database (no rows yet) and on a database this function
    already ran on (every row already has an entry).
    """
    from app.persistence.tables import ChainEntryRow, DecisionRecordRow

    with Session(engine) as session:
        existing_ref_ids = set(
            session.scalars(
                select(ChainEntryRow.ref_id).where(ChainEntryRow.kind == "decision")
            )
        )
        rows = session.scalars(
            select(DecisionRecordRow).order_by(DecisionRecordRow.position)
        ).all()
        missing = [row for row in rows if row.id not in existing_ref_ids]
        if not missing:
            return

        last_hash = session.scalar(
            select(ChainEntryRow.record_hash).order_by(ChainEntryRow.seq.desc()).limit(1)
        )
        prev_hash = last_hash if last_hash is not None else GENESIS_PREV_HASH
        for row in missing:
            record = DecisionRecord.model_validate_json(row.payload)
            record_hash = compute_decision_entry_hash(record, prev_hash)
            session.add(
                ChainEntryRow(
                    kind="decision",
                    ref_id=row.id,
                    payload=None,
                    prev_hash=prev_hash,
                    record_hash=record_hash,
                )
            )
            prev_hash = record_hash
        session.commit()


_LEGACY_OWNER = "legacy"


def ensure_owner_id_column(engine: Engine) -> None:
    """Add `owner_id` to pre-existing `decision_record` tables (idempotent)."""
    inspector = inspect(engine)
    if "decision_record" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("decision_record")}
    if "owner_id" in columns:
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                f"ALTER TABLE decision_record ADD COLUMN owner_id VARCHAR NOT NULL "
                f"DEFAULT '{_LEGACY_OWNER}'"
            )
        )


_API_TABLES = ("rules_document", "decision_record", "chain_entries")
_SUPABASE_BROWSER_ROLES = ("anon", "authenticated")


def _supabase_browser_roles_present(conn) -> tuple[str, ...]:
    """Roles used by Supabase PostgREST; absent on vanilla Postgres (e.g. Render)."""
    rows = conn.execute(
        text(
            "SELECT rolname FROM pg_roles "
            "WHERE rolname IN ('anon', 'authenticated')"
        )
    ).scalars().all()
    return tuple(r for r in _SUPABASE_BROWSER_ROLES if r in rows)


def ensure_postgres_api_lockdown(engine: Engine) -> None:
    """Supabase demo: RLS on; revoke browser roles only when they exist.

    On Render Postgres the API connects with ``DATABASE_URL`` and there is no
    ``anon``/``authenticated`` role — unconditional ``REVOKE`` would abort boot.
    """
    if not engine.dialect.name.startswith("postgres"):
        return
    with engine.begin() as conn:
        revoke_targets = ", ".join(_supabase_browser_roles_present(conn))
        for table in _API_TABLES:
            conn.execute(text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
            if revoke_targets:
                conn.execute(
                    text(f'REVOKE ALL ON TABLE "{table}" FROM {revoke_targets}')
                )
