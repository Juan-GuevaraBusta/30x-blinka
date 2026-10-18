"""Generate `backend/sql/seed_demo.sql` from the shared demo fixtures (T11).

Builds the exact same demo `RulesConfig` and the same 3 vendor-agreement
terms `seed_demo.py` (T10) uses -- via `scripts._demo_fixtures`, so both
scripts stay in sync -- validates them through the real Pydantic models
(`RulesConfig`, `VendorAgreement`), and serializes them into a Postgres
(Supabase-dialect) SQL file: `INSERT ... WHERE NOT EXISTS` for
`rules_document`, `INSERT ... ON CONFLICT (vendor_key, version) DO NOTHING`
per vendor for `vendor_agreement_version` -- matching the dialect already
used in `backend/sql/supabase_schema.sql`, which this file sits next to.

This SQL path intentionally bypasses `chain_entries` (see the header this
script writes into the output file); `seed_demo.py` through the real API is
the preferred way to seed the demo.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.api.tenancy import DEMO_BASE_CURRENCY, DEMO_COMPANY_ID, DEMO_COMPANY_NAME
from app.api.tenancy import normalize_company_name as _normalize_company_name

from scripts._demo_fixtures import (
    REPO_ROOT,
    build_demo_agreements,
    build_demo_rules_config,
    pick_approver_email,
)

DEFAULT_OUTPUT: Path = REPO_ROOT / "backend" / "sql" / "seed_demo.sql"

# Fixed, deterministic `confirmed_at` for the SQL-only demo rows (no clock, no
# network -- this script is pure except for the final file write in `main`).
_SEED_CONFIRMED_AT = "2026-01-01T00:00:00+00:00"

_HEADER = """\
-- Semilla de demo para Postgres/Supabase (bypassa la cadena de auditoria) --------------------
--
-- Estos INSERT escriben directamente en `rules_document` y
-- `vendor_agreement_version` sin pasar por la API real (`PUT /rules`,
-- `PUT /agreements/{vendor_key}`), por lo que NO agregan la fila
-- correspondiente en `chain_entries` que el flujo de confirmacion real
-- (`SqlStore.confirm_agreement`) escribe en la misma transaccion.
--
-- Para la demo, prefiere `backend/scripts/seed_demo.py --apply --with-rules`
-- (usa la API real y mantiene la cadena de auditoria intacta). Este archivo
-- SQL es solo para inspeccion rapida local -- por ejemplo abrir la base de
-- datos directamente y ver datos de ejemplo ya cargados -- nunca para un
-- entorno donde el gate de auditoria deba quedar completo.
--
-- Generado por backend/scripts/generate_seed_sql.py a partir de los mismos
-- modelos Pydantic (RulesConfig / VendorAgreement) que usa seed_demo.py.
-- No editar a mano: regenerar con ese script si cambian los datos de demo.
"""


def _sql_string_literal(value: str) -> str:
    """Single-quoted SQL string literal, with `'` doubled (standard escaping)."""
    return "'" + value.replace("'", "''") + "'"


def render_sql() -> str:
    """Pure: builds + validates the demo fixtures and renders the SQL text.

    No file I/O here -- `main()` is the only place that writes to disk, so
    this function alone is what tests call to validate the embedded JSON.
    """
    demo_rules = build_demo_rules_config()
    demo_agreements = build_demo_agreements()
    confirmed_by = pick_approver_email()

    company = _sql_string_literal(DEMO_COMPANY_ID)
    company_name = _sql_string_literal(DEMO_COMPANY_NAME)
    company_name_key = _sql_string_literal(_normalize_company_name(DEMO_COMPANY_NAME))
    base_currency = _sql_string_literal(DEMO_BASE_CURRENCY)
    lines: list[str] = [_HEADER, "", "-- 0. Empresa demo (T9.8)", ""]
    lines.append(
        "INSERT INTO companies (id, name, name_key, base_currency, is_demo, created_by, "
        "created_at)\n"
        f"VALUES ({company}, {company_name}, {company_name_key}, {base_currency}, TRUE, "
        f"NULL, {_sql_string_literal(_SEED_CONFIRMED_AT)})\n"
        "ON CONFLICT (id) DO NOTHING;"
    )
    lines += ["", "-- 1. Reglas base (rules_document)", ""]
    rules_json = demo_rules.model_dump_json()
    lines.append(
        "INSERT INTO rules_document (id, payload, company_id)\n"
        "SELECT COALESCE((SELECT MAX(id) FROM rules_document), 0) + 1, "
        f"{_sql_string_literal(rules_json)}, {company}\n"
        f"WHERE NOT EXISTS (SELECT 1 FROM rules_document WHERE company_id = {company});"
    )
    lines.append("")
    lines.append("-- 2. Acuerdos de proveedores demo (vendor_agreement_version, v1 activa)")
    lines.append("")
    for vendor_key, terms in demo_agreements.items():
        terms_json = terms.model_dump_json()
        lines.append(
            "INSERT INTO vendor_agreement_version "
            "(company_id, vendor_key, version, terms_json, source_sha256, spans_json, "
            "confirmed_by, confirmed_at, status)\n"
            "VALUES (\n"
            f"    {company},\n"
            f"    {_sql_string_literal(vendor_key)},\n"
            "    1,\n"
            f"    {_sql_string_literal(terms_json)},\n"
            "    NULL,\n"
            f"    {_sql_string_literal('[]')},\n"
            f"    {_sql_string_literal(confirmed_by)},\n"
            f"    {_sql_string_literal(_SEED_CONFIRMED_AT)},\n"
            f"    {_sql_string_literal('active')}\n"
            ")\n"
            "ON CONFLICT (company_id, vendor_key, version) DO NOTHING;"
        )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Regenerate backend/sql/seed_demo.sql from the shared demo fixtures."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output SQL file path (default: {DEFAULT_OUTPUT}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    sql = render_sql()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(sql, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
