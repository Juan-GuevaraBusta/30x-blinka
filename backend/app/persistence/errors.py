"""Persistence-layer errors (T4.2)."""

from __future__ import annotations


class RulesMissing(Exception):
    """No rules row exists in the database."""


class MissingDatabaseUrlError(Exception):
    """DATABASE_URL is absent or empty."""

    def __init__(self) -> None:
        super().__init__("missing_database_url")
