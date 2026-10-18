"""SQLAlchemy table definitions for rules, decision records, and the T5.10
append-only hash chain."""

from __future__ import annotations

from sqlalchemy import Integer, MetaData, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

metadata = MetaData()


class Base(DeclarativeBase):
    metadata = metadata


class RulesDocument(Base):
    __tablename__ = "rules_document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class DecisionRecordRow(Base):
    __tablename__ = "decision_record"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    invoice_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class ChainEntryRow(Base):
    """T5.10 (D055): the append-only hash chain, kept in its own table
    instead of columns on `DecisionRecordRow`, precisely so nothing about a
    decision row's chain state is ever UPDATEd (see `app.records.chain`'s
    module docstring for why that matters for a tamper-evident log).

    `seq` (autoincrement) is the only ordering; a row here is written exactly
    once, by `SqlStore.add_decision` (kind="decision") or
    `SqlStore.add_human_event` (kind="human_event"), and read-only everywhere
    else -- including `SqlStore.verify_chain` and the one-time boot backfill
    for rows that pre-date this table
    (`app.persistence.migrations.ensure_decision_chain_backfilled`).

    `ref_id` is the decision id for both kinds (a `human_event` entry is
    about that decision, even though the event itself has no id of its own).
    `payload` is `None` for a `decision` entry -- `SqlStore.verify_chain`
    re-derives what to hash from the *current* `DecisionRecordRow` (minus
    `human_events`) instead, which is what lets a direct-DB edit of that row
    still be caught. For a `human_event` entry, `payload` is the canonical
    JSON of that event, stored once and never touched again -- there is no
    other place a human event is kept on its own.
    """

    __tablename__ = "chain_entries"

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    ref_id: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    prev_hash: Mapped[str] = mapped_column(String, nullable=False)
    record_hash: Mapped[str] = mapped_column(String, nullable=False)
