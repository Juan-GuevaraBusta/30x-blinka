"""Resolve DATABASE_URL from a mapping without touching os.environ or config."""

from __future__ import annotations

from collections.abc import Mapping

from app.persistence.errors import MissingDatabaseUrlError


def database_url_from_mapping(mapping: Mapping[str, str]) -> str:
    raw = mapping.get("DATABASE_URL")
    if raw is None or not str(raw).strip():
        raise MissingDatabaseUrlError()
    return str(raw).strip()
