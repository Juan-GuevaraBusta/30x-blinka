"""T1.7 — Golden set: labels, ground-truth extraction, consistency with catalog."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app.models.domain import Extraction

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "data" / "invoices" / "catalog.json"
FX_PATH = REPO_ROOT / "data" / "fx.json"
COMPANY_PATH = REPO_ROOT / "data" / "company.json"
GOLDEN_DIR = REPO_ROOT / "data" / "golden"

GOLDEN_DUP_PAY_FIRST = frozenset({"dev-012", "hold-001"})
GOLDEN_DUP_SECOND = frozenset({"dev-013", "hold-004"})
FX_AS_OF = date(2026, 3, 1)
FX_TOLERANCE = 0.01

REASON_MIN_LEN = 20


def _load_catalog() -> list[dict]:
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    return data


def _catalog_by_split(split: str) -> dict[str, dict]:
    return {e["id"]: e for e in _load_catalog() if e["split"] == split}


def _load_golden(split: str) -> dict:
    path = GOLDEN_DIR / f"{split}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _fx_rates() -> dict[str, float]:
    fx = json.loads(FX_PATH.read_text(encoding="utf-8"))
    return fx["rates"]


def _expected_from_catalog(catalog_row: dict) -> tuple[str, list[str]]:
    invoice_id = catalog_row["id"]
    if invoice_id in GOLDEN_DUP_PAY_FIRST:
        return "PAGAR", []
    return catalog_row["expected_decision"], list(catalog_row["expected_rules"])


def _golden_path(split: str) -> Path:
    return GOLDEN_DIR / f"{split}.json"


def test_golden_dev_file_exists_with_schema() -> None:
    golden = _load_golden("dev")
    assert golden["schema_version"] == 1
    assert golden["split"] == "dev"
    assert golden["dataset_review"]["review_passes"] == 2
    assert len(golden["entries"]) == 34


def test_golden_holdout_file_exists_with_schema() -> None:
    golden = _load_golden("holdout")
    assert golden["schema_version"] == 1
    assert golden["split"] == "holdout"
    assert golden["dataset_review"]["review_passes"] == 2
    assert len(golden["entries"]) == 10


def test_golden_entries_match_catalog_ids_paths_received_at() -> None:
    for split in ("dev", "holdout"):
        catalog = _catalog_by_split(split)
        golden = _load_golden(split)
        assert set(e["invoice_id"] for e in golden["entries"]) == set(catalog.keys())
        for entry in golden["entries"]:
            cat = catalog[entry["invoice_id"]]
            assert entry["catalog_path"] == cat["path"]
            assert entry["case"] == cat["case"]
            assert entry["received_at"] == cat["received_at"]


def test_golden_extraction_validates_as_extraction_model() -> None:
    for split in ("dev", "holdout"):
        golden = _load_golden(split)
        for entry in golden["entries"]:
            Extraction.model_validate(entry["extraction"])


def test_golden_fx_amount_base_matches_fx_json() -> None:
    rates = _fx_rates()
    for split in ("dev", "holdout"):
        golden = _load_golden(split)
        for entry in golden["entries"]:
            ext = entry["extraction"]
            currency = ext.get("currency")
            amount = ext.get("amount")
            if currency is None or currency == "XXX" or amount is None:
                continue
            if currency == "USD":
                if ext.get("amount_base") is not None:
                    assert abs(ext["amount_base"] - amount) <= FX_TOLERANCE
                continue
            assert currency in rates
            expected_base = round(amount * rates[currency], 2)
            assert ext.get("amount_base") is not None
            assert abs(ext["amount_base"] - expected_base) <= FX_TOLERANCE
            fx = ext.get("fx")
            assert fx is not None
            assert fx["rate"] == rates[currency]
            assert fx["date"] == FX_AS_OF.isoformat()


def test_golden_special_missing_fields_dev_029_030_033() -> None:
    golden = _load_golden("dev")
    by_id = {e["invoice_id"]: e for e in golden["entries"]}
    assert by_id["dev-029"]["extraction"]["amount"] is None
    assert by_id["dev-030"]["extraction"]["due_date"] is None
    ext33 = by_id["dev-033"]["extraction"]
    assert ext33["currency"] == "XXX"
    assert ext33.get("fx") is None
    assert ext33.get("amount_base") is None


def test_golden_dup_exact_order_overrides_catalog() -> None:
    catalog = {e["id"]: e for e in _load_catalog()}
    for split in ("dev", "holdout"):
        golden = _load_golden(split)
        for entry in golden["entries"]:
            iid = entry["invoice_id"]
            cat = catalog[iid]
            exp_dec, exp_rules = _expected_from_catalog(cat)
            assert entry["expected_decision"] == exp_dec
            assert entry["expected_rules"] == exp_rules
            if iid in GOLDEN_DUP_PAY_FIRST | GOLDEN_DUP_SECOND:
                assert entry.get("notes")


def test_golden_non_dup_expected_matches_catalog() -> None:
    catalog = {e["id"]: e for e in _load_catalog()}
    dup_ids = GOLDEN_DUP_PAY_FIRST | GOLDEN_DUP_SECOND
    for split in ("dev", "holdout"):
        golden = _load_golden(split)
        for entry in golden["entries"]:
            iid = entry["invoice_id"]
            if iid in dup_ids:
                continue
            cat = catalog[iid]
            assert entry["expected_decision"] == cat["expected_decision"]
            assert entry["expected_rules"] == cat["expected_rules"]


def test_golden_ledger_seed_matches_catalog() -> None:
    catalog = {e["id"]: e for e in _load_catalog()}
    for split in ("dev", "holdout"):
        golden = _load_golden(split)
        for entry in golden["entries"]:
            cat = catalog[entry["invoice_id"]]
            expected_seed = cat.get("ledger_seed", [])
            assert entry["ledger_seed"] == expected_seed


def test_golden_manual_block_matches_catalog() -> None:
    catalog = {e["id"]: e for e in _load_catalog()}
    for split in ("dev", "holdout"):
        golden = _load_golden(split)
        for entry in golden["entries"]:
            cat = catalog[entry["invoice_id"]]
            assert entry["manual_block"] == cat["manual_block"]


def test_golden_r12_dev_034() -> None:
    golden = _load_golden("dev")
    row = next(e for e in golden["entries"] if e["invoice_id"] == "dev-034")
    assert row["manual_block"] is True
    assert row["expected_decision"] == "FRENAR"
    assert row["expected_rules"] == ["R12"]


def test_golden_contract_confirmed_for_allowed_non_r01() -> None:
    allowed = set(json.loads(COMPANY_PATH.read_text(encoding="utf-8"))["allowed_beneficiaries"])
    for split in ("dev", "holdout"):
        catalog = _catalog_by_split(split)
        golden = _load_golden(split)
        for entry in golden["entries"]:
            cat = catalog[entry["invoice_id"]]
            beneficiary = cat["beneficiary"]
            if cat["case"] == "r01":
                continue
            if beneficiary in allowed:
                assert entry["contract_confirmed"] is True
                assert entry.get("contract_path")
                assert entry.get("contract_terms")


def test_golden_r01_no_contract_confirmed() -> None:
    for split in ("dev", "holdout"):
        catalog = _catalog_by_split(split)
        golden = _load_golden(split)
        for entry in golden["entries"]:
            if catalog[entry["invoice_id"]]["case"] != "r01":
                continue
            assert entry["contract_confirmed"] is False
            assert "contract_path" not in entry or entry.get("contract_path") is None


def test_golden_review_passes_two_everywhere() -> None:
    for split in ("dev", "holdout"):
        golden = _load_golden(split)
        for entry in golden["entries"]:
            assert entry["review_passes"] == 2


def test_golden_reason_non_empty_spanish() -> None:
    for split in ("dev", "holdout"):
        golden = _load_golden(split)
        for entry in golden["entries"]:
            reason = entry["reason"]
            assert isinstance(reason, str)
            assert len(reason.strip()) >= REASON_MIN_LEN


def test_golden_dev_028_recipient_override() -> None:
    golden = _load_golden("dev")
    row = next(e for e in golden["entries"] if e["invoice_id"] == "dev-028")
    assert row["extraction"]["recipient"] == "Otra Empresa Fantasma SA"
