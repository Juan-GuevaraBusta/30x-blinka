"""Postgres boot lockdown: Supabase roles optional (Render has no anon/authenticated)."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.persistence.migrations import ensure_postgres_api_lockdown


def _stmt_strings(conn: MagicMock) -> list[str]:
    out: list[str] = []
    for call in conn.execute.call_args_list:
        arg = call[0][0]
        out.append(str(arg))
    return out


def test_lockdown_enables_rls_without_revoke_on_vanilla_postgres() -> None:
    engine = MagicMock()
    engine.dialect.name = "postgresql"
    conn = MagicMock()
    role_result = MagicMock()
    role_result.scalars.return_value.all.return_value = []
    conn.execute.return_value = role_result
    begin_ctx = MagicMock()
    begin_ctx.__enter__.return_value = conn
    begin_ctx.__exit__.return_value = False
    engine.begin.return_value = begin_ctx

    ensure_postgres_api_lockdown(engine)

    stmts = _stmt_strings(conn)
    assert any("ENABLE ROW LEVEL SECURITY" in s for s in stmts)
    assert not any("REVOKE" in s for s in stmts)


def test_lockdown_revokes_when_supabase_roles_exist() -> None:
    engine = MagicMock()
    engine.dialect.name = "postgresql"
    conn = MagicMock()

    def execute_side_effect(stmt, *_args, **_kwargs):
        if "pg_roles" in str(stmt):
            role_result = MagicMock()
            role_result.scalars.return_value.all.return_value = ["anon", "authenticated"]
            return role_result
        return MagicMock()

    conn.execute.side_effect = execute_side_effect
    begin_ctx = MagicMock()
    begin_ctx.__enter__.return_value = conn
    begin_ctx.__exit__.return_value = False
    engine.begin.return_value = begin_ctx

    ensure_postgres_api_lockdown(engine)

    stmts = _stmt_strings(conn)
    assert any("REVOKE ALL" in s and "anon" in s for s in stmts)


def test_lockdown_noop_on_sqlite() -> None:
    engine = MagicMock()
    engine.dialect.name = "sqlite"
    ensure_postgres_api_lockdown(engine)
    engine.begin.assert_not_called()
