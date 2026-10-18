"""Every persisted table must be covered by the Supabase API lockdown (RLS + REVOKE)."""

from __future__ import annotations

from app.persistence.migrations import _API_TABLES
from app.persistence.tables import metadata


def test_every_table_is_locked_down_for_supabase_browser_roles() -> None:
    # vendor_agreement_version was missing; the public anon key could read it.
    assert set(metadata.tables) <= set(_API_TABLES)
