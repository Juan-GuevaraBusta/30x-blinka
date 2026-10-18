"""SQL persistence. Importing this module does not open engines or files."""

from __future__ import annotations

from sqlalchemy.engine import Engine

from app.persistence.errors import MissingDatabaseUrlError, RulesMissing
from app.persistence.migrations import ensure_decision_chain_backfilled
from app.persistence.seed import seed_rules
from app.persistence.sql_store import SqlStore
from app.persistence.tables import metadata
from app.persistence.url import database_url_from_mapping


def init_database(engine: Engine) -> None:
    metadata.create_all(bind=engine)
    # T5.10 (D055): `create_all` creates `chain_entries` on any database
    # (new or pre-existing) since it didn't exist before, but it cannot
    # populate it for `decision_record` rows that pre-date this table.
    # Idempotent: a no-op once every row has its entry.
    ensure_decision_chain_backfilled(engine)


__all__ = [
    "MissingDatabaseUrlError",
    "RulesMissing",
    "SqlStore",
    "database_url_from_mapping",
    "init_database",
    "seed_rules",
]
