"""SQL persistence. Importing this module does not open engines or files."""

from __future__ import annotations

from sqlalchemy.engine import Engine

from app.persistence.errors import MissingDatabaseUrlError, RulesMissing
from app.persistence.seed import seed_rules
from app.persistence.sql_store import SqlStore
from app.persistence.tables import metadata
from app.persistence.url import database_url_from_mapping


def init_database(engine: Engine) -> None:
    metadata.create_all(bind=engine)


__all__ = [
    "MissingDatabaseUrlError",
    "RulesMissing",
    "SqlStore",
    "database_url_from_mapping",
    "init_database",
    "seed_rules",
]
