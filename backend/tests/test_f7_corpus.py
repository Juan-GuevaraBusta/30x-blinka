"""T7.6 — Structural checks for the f7 corpus (series, variable pay, approval policy).

Separate, synthetic-only (I6) split from dev/holdout. ``data/f7/rules.json``
cannot validate against the frozen ``RulesConfig`` yet (it adds
``approval_policy``/``payment_series``/``variable_pricing``, which land one
RulesConfig field at a time in T7.1-T7.3); that is tracked here as a strict
xfail, not silently skipped.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from app.models.rules_config import load_rules_config
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[2]
F7_DIR = REPO_ROOT / "data" / "invoices" / "f7"
CATALOG_PATH = F7_DIR / "catalog.json"
GENERATOR_PATH = F7_DIR / "generate_f7.py"
GOLDEN_PATH = REPO_ROOT / "data" / "golden" / "f7.json"
F7_RULES_PATH = REPO_ROOT / "data" / "f7" / "rules.json"
BASE_RULES_PATH = REPO_ROOT / "data" / "rules.json"

FOOTER = "Documento ficticio. No representa a ninguna empresa real."

EXPECTED_CASE_BY_ID: dict[str, tuple[str, str, str]] = {
    # id: (feature, expected_decision, at least one expected rule)
    "f7-001": ("T7.2", "PAGAR", ""),
    "f7-002": ("T7.2", "ESCALAR", "R15"),
    "f7-003": ("T7.2", "ESCALAR", "R15"),
    "f7-004": ("T7.2", "FRENAR", "R16"),
    "f7-005": ("T7.2", "FRENAR", "R17"),
    "f7-006": ("T7.2", "PAGAR", ""),
    "f7-007": ("T7.2", "PAGAR", ""),
    "f7-008": ("T7.3", "ESCALAR", "R06"),
    "f7-009": ("T7.3", "FRENAR", "R19"),
    "f7-010": ("T7.3", "ESCALAR", "R06"),
    "f7-011": ("T7.3", "FRENAR", "R19"),
    "f7-012": ("T7.1", "ESCALAR", "R14"),
    "f7-013": ("T7.1", "ESCALAR", "R14"),
    "f7-014": ("T7.1", "PAGAR", ""),
    "f7-015": ("T7.2", "FRENAR", "R16"),
    "f7-016": ("T7.3", "ESCALAR", "R13"),
}

ALLOWED_CATALOG_KEYS = frozenset(
    {
        "id",
        "split",
        "feature",
        "path",
        "channel",
        "case",
        "expected_decision",
        "expected_rules",
        "beneficiary",
        "amount",
        "currency",
        "invoice_number",
        "due_date",
        "recipient",
        "department",
        "received_at",
        "manual_block",
        "notes",
        "ledger_seed",
    }
)


def _load_catalog() -> list[dict]:
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    return data


def _load_golden() -> dict:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_f7_catalog_has_sixteen_entries_with_valid_schema() -> None:
    catalog = _load_catalog()
    assert len(catalog) == 16
    ids: set[str] = set()
    for entry in catalog:
        assert entry["split"] == "f7"
        assert set(entry.keys()) <= ALLOWED_CATALOG_KEYS
        assert entry["id"] not in ids
        ids.add(entry["id"])
    assert ids == set(EXPECTED_CASE_BY_ID)


def test_f7_catalog_paths_exist_under_f7_folder() -> None:
    for entry in _load_catalog():
        rel = entry["path"]
        assert rel.startswith("data/invoices/f7/")
        assert (REPO_ROOT / rel).is_file(), rel


def test_f7_text_and_email_channels_contain_footer() -> None:
    for entry in _load_catalog():
        if entry["channel"] not in ("email", "chat", "txt"):
            continue
        text = (REPO_ROOT / entry["path"]).read_text(encoding="utf-8")
        assert FOOTER in text


def test_regenerating_f7_does_not_change_catalog_or_file_hashes() -> None:
    catalog = _load_catalog()
    catalog_bytes = CATALOG_PATH.read_bytes()
    paths = sorted(REPO_ROOT / e["path"] for e in catalog)
    hashes_before = {p: _sha256(p) for p in paths}

    subprocess.run([sys.executable, str(GENERATOR_PATH)], check=True, cwd=REPO_ROOT)

    assert CATALOG_PATH.read_bytes() == catalog_bytes
    for p in paths:
        assert _sha256(p) == hashes_before[p]


def test_dev_holdout_corpus_regeneration_still_unaffected() -> None:
    """The frozen dev/holdout generator+catalog test keeps passing (T1.6 regression)."""
    dev_generator = REPO_ROOT / "data" / "invoices" / "generate.py"
    dev_catalog = REPO_ROOT / "data" / "invoices" / "catalog.json"
    before = dev_catalog.read_bytes()
    subprocess.run([sys.executable, str(dev_generator)], check=True, cwd=REPO_ROOT)
    assert dev_catalog.read_bytes() == before


def test_f7_golden_has_sixteen_entries_with_t71_enabled() -> None:
    """T7.1 (D059) lands and enables its own feature; T7.2/T7.3 stay disabled
    until they land too (docs/T7_6_SPEC.md §2)."""
    golden = _load_golden()
    assert golden["schema_version"] == 1
    assert golden["split"] == "f7"
    assert golden["enabled_features"] == ["T7.1"]
    assert golden["dataset_review"]["review_passes"] == 2
    assert len(golden["entries"]) == 16
    assert {e["invoice_id"] for e in golden["entries"]} == set(EXPECTED_CASE_BY_ID)


def test_f7_golden_entries_have_feature_decision_rules_and_two_review_passes() -> None:
    for entry in _load_golden()["entries"]:
        invoice_id = entry["invoice_id"]
        feature, expected_decision, must_contain_rule = EXPECTED_CASE_BY_ID[invoice_id]
        assert entry["feature"] == feature
        assert entry["expected_decision"] == expected_decision
        if must_contain_rule:
            assert must_contain_rule in entry["expected_rules"]
        else:
            assert entry["expected_rules"] == []
        assert entry["review_passes"] == 2
        assert len(entry["reason"]) >= 20


def test_f7_golden_approval_cases_carry_route_and_required() -> None:
    golden = _load_golden()
    by_id = {e["invoice_id"]: e for e in golden["entries"]}
    assert by_id["f7-012"]["expected_approval"] == {"route_id": "alto-monto", "required": 2}
    assert by_id["f7-013"]["expected_approval"] == {"route_id": "marketing-cfo", "required": 1}
    assert by_id["f7-014"]["expected_approval"] == {"route_id": "default", "required": 0}
    for entry in golden["entries"]:
        if entry["invoice_id"] not in ("f7-012", "f7-013", "f7-014"):
            assert "expected_approval" not in entry


def test_f7_golden_series_cases_ledger_seed_carries_due_date() -> None:
    golden = _load_golden()
    by_id = {e["invoice_id"]: e for e in golden["entries"]}
    for invoice_id in ("f7-004", "f7-005", "f7-015"):
        seeds = by_id[invoice_id]["ledger_seed"]
        assert seeds, invoice_id
        for row in seeds:
            assert "due_date" in row


def test_f7_rules_json_is_base_rules_plus_new_sections() -> None:
    base = json.loads(BASE_RULES_PATH.read_text(encoding="utf-8"))
    f7 = json.loads(F7_RULES_PATH.read_text(encoding="utf-8"))
    for key in ("approval_policy", "payment_series", "variable_pricing"):
        assert key in f7
        assert key not in base
    # Base-rules.json keys stay byte-identical in f7's copy, except the
    # beneficiary allowlist, which may only grow (new f7-* providers).
    for key, value in base.items():
        if key == "allowed_beneficiaries":
            assert set(value) <= set(f7[key])
            continue
        assert f7[key] == value


@pytest.mark.xfail(
    strict=True,
    reason=(
        "data/f7/rules.json declares payment_series/variable_pricing, which "
        "RulesConfig does not accept yet (extra=forbid); approval_policy landed "
        "with T7.1. Each of T7.2/T7.3 adds its own field additively; once both "
        "have landed this should start passing and the xfail must be removed."
    ),
)
def test_f7_rules_json_validates_against_rules_config() -> None:
    load_rules_config(F7_RULES_PATH)


def test_f7_rules_json_fails_only_on_the_remaining_new_sections() -> None:
    """Pin down *why* the xfail above fails, so a schema drift elsewhere is caught."""
    with pytest.raises(ValidationError) as excinfo:
        load_rules_config(F7_RULES_PATH)
    errors = excinfo.value.errors()
    extra_fields = {
        err["loc"][0]
        for err in errors
        if err["type"] == "extra_forbidden" and err["loc"]
    }
    assert extra_fields == {"payment_series", "variable_pricing"}
