"""Unit tests for `backend/scripts/generate_seed_sql.py` (T11).

Pulls the JSON blobs embedded in the generated SQL back out (simple string
parsing -- this doesn't need a real SQL parser) and validates each one
against the real `RulesConfig` / `VendorAgreement` Pydantic models.
"""

from __future__ import annotations

import json
import re

from app.models.agreement import parse_vendor_agreement
from app.models.rules_config import RulesConfig
from scripts._demo_fixtures import DEMO_VENDOR_NAMES
from scripts.generate_seed_sql import render_sql

_QUOTED_JSON = re.compile(r"'((?:[^']|'')*)'")


def _extract_json_blobs(sql: str) -> list[dict]:
    blobs: list[dict] = []
    for match in _QUOTED_JSON.finditer(sql):
        candidate = match.group(1).replace("''", "'")
        if not candidate.startswith("{"):
            continue
        blobs.append(json.loads(candidate))
    return blobs


def test_generated_sql_has_spanish_header_about_bypassing_the_chain() -> None:
    sql = render_sql()

    assert "chain_entries" in sql
    assert "seed_demo.py" in sql
    # Spanish header, per the ODD task spec.
    assert any(word in sql for word in ("auditoría", "cadena"))


def test_generated_sql_uses_rules_document_not_exists_pattern() -> None:
    sql = render_sql()

    assert "INSERT INTO rules_document" in sql
    assert (
        "WHERE NOT EXISTS (SELECT 1 FROM rules_document WHERE company_id = 'demo-acme')" in sql
    )


def test_generated_sql_uses_on_conflict_do_nothing_for_agreements() -> None:
    sql = render_sql()

    assert sql.count("ON CONFLICT (company_id, vendor_key, version) DO NOTHING") == 3
    assert "INSERT INTO vendor_agreement_version" in sql
    for name in DEMO_VENDOR_NAMES:
        assert name in sql


def test_embedded_json_blobs_validate_against_real_models() -> None:
    sql = render_sql()
    blobs = _extract_json_blobs(sql)

    rules_blobs = [b for b in blobs if "company" in b and "allowed_beneficiaries" in b]
    agreement_blobs = [b for b in blobs if "kind" in b and "vendor_name" in b]

    assert len(rules_blobs) == 1
    assert len(agreement_blobs) == 3

    rules = RulesConfig.model_validate(rules_blobs[0])
    assert rules.approval_policy is not None
    assert rules.approval_policy.routes[-1].match.is_empty()

    vendor_names = set()
    for blob in agreement_blobs:
        agreement = parse_vendor_agreement(blob)
        vendor_names.add(agreement.vendor_name)
    assert vendor_names == set(DEMO_VENDOR_NAMES)
