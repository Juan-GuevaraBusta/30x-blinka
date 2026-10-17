"""T1.6 — Structural checks for synthetic invoice corpus (dev + holdout)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INVOICES_DIR = REPO_ROOT / "data" / "invoices"
CATALOG_PATH = INVOICES_DIR / "catalog.json"
GENERATOR_PATH = INVOICES_DIR / "generate.py"
COMPANY_PATH = REPO_ROOT / "data" / "company.json"

FOOTER = "Documento ficticio. No representa a ninguna empresa real."

ALLOWED_CATALOG_KEYS = frozenset(
    {
        "id",
        "split",
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

LEDGER_SEED_KEYS = frozenset(
    {
        "beneficiary",
        "amount_base",
        "currency",
        "invoice_number",
        "received_at",
        "decision",
    }
)

DEV_CASE_COUNTS: dict[str, int] = {
    "normal_pay": 8,
    "fx_pay": 2,
    "fx_r04": 1,
    "dup_exact": 2,
    "dup_probable": 1,
    "r01": 3,
    "r06": 3,
    "r04_only": 2,
    "r02_r04": 1,
    "r03": 2,
    "r07": 2,
    "r08": 1,
    "r09_r11": 2,
    "r13": 2,
    "r10": 1,
    "r12": 1,
}

HOLDOUT_CASE_COUNTS: dict[str, int] = {
    "normal_pay": 3,
    "fx_pay": 1,
    "dup_exact": 1,
    "r01": 1,
    "r06": 1,
    "r04_only": 1,
    "r07": 1,
    "r13": 1,
}

DUP_EXACT_INVOICE_NUMBERS = frozenset({"INV-GX-DUP-EXACT", "INV-H-GX-1"})

R01_OUTSIDE = ("Nuevo Socio Fantasma SAS", "Taller Sin Alta Ltda")


def _load_catalog() -> list[dict]:
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    return data


def _invoice_artifact_paths(split: str) -> list[Path]:
    folder = INVOICES_DIR / split
    if not folder.is_dir():
        return []
    return [
        p
        for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in {".pdf", ".png", ".eml", ".txt"}
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_dev_has_thirty_four_invoice_files() -> None:
    assert len(_invoice_artifact_paths("dev")) == 34


def test_holdout_has_ten_invoice_files() -> None:
    assert len(_invoice_artifact_paths("holdout")) == 10


def test_catalog_has_forty_four_entries_with_valid_schema() -> None:
    catalog = _load_catalog()
    assert len(catalog) == 44
    ids: set[str] = set()
    for entry in catalog:
        assert set(entry.keys()) <= ALLOWED_CATALOG_KEYS
        extra = set(entry.keys()) - ALLOWED_CATALOG_KEYS
        assert not extra
        assert entry["id"] not in ids
        ids.add(entry["id"])
        if "ledger_seed" in entry:
            for seed in entry["ledger_seed"]:
                assert set(seed.keys()) == LEDGER_SEED_KEYS
                assert seed["decision"] == "PAGAR"


def test_catalog_paths_exist_and_split_matches_folder() -> None:
    catalog = _load_catalog()
    for entry in catalog:
        rel = entry["path"]
        assert rel.startswith("data/invoices/")
        full = REPO_ROOT / rel
        assert full.is_file(), rel
        if entry["split"] == "dev":
            assert "/dev/" in rel
        else:
            assert entry["split"] == "holdout"
            assert "/holdout/" in rel


def test_dev_and_holdout_case_counts_match_manifest() -> None:
    catalog = _load_catalog()
    dev = Counter(e["case"] for e in catalog if e["split"] == "dev")
    hold = Counter(e["case"] for e in catalog if e["split"] == "holdout")
    assert dict(dev) == DEV_CASE_COUNTS
    assert dict(hold) == HOLDOUT_CASE_COUNTS


def test_at_least_four_files_per_channel() -> None:
    catalog = _load_catalog()
    channels = Counter(e["channel"] for e in catalog)
    for ch in ("pdf_text", "image", "email", "chat"):
        assert channels[ch] >= 4


def test_text_and_email_channels_contain_footer() -> None:
    catalog = _load_catalog()
    for entry in catalog:
        if entry["channel"] not in ("email", "chat"):
            continue
        text = (REPO_ROOT / entry["path"]).read_text(encoding="utf-8")
        assert FOOTER in text


def test_pdf_png_and_eml_magic_bytes_and_headers() -> None:
    catalog = _load_catalog()
    for entry in catalog:
        path = REPO_ROOT / entry["path"]
        raw = path.read_bytes()
        if entry["channel"] == "pdf_text":
            assert raw.startswith(b"%PDF")
        elif entry["channel"] == "image":
            assert raw.startswith(b"\x89PNG\r\n\x1a\n")
        elif entry["channel"] == "email":
            text = raw.decode("utf-8")
            assert "From:" in text
            assert "Subject:" in text


def test_holdout_paths_not_under_dev_folder() -> None:
    catalog = _load_catalog()
    dev_names = {p.name for p in _invoice_artifact_paths("dev")}
    for entry in catalog:
        if entry["split"] != "holdout":
            continue
        name = Path(entry["path"]).name
        assert name not in dev_names


def test_r01_beneficiaries_not_in_allowed_list() -> None:
    allowed = set(json.loads(COMPANY_PATH.read_text(encoding="utf-8"))["allowed_beneficiaries"])
    catalog = _load_catalog()
    for entry in catalog:
        if entry["case"] != "r01":
            continue
        assert entry["beneficiary"] in R01_OUTSIDE
        assert entry["beneficiary"] not in allowed


def test_r10_uses_currency_xxx() -> None:
    catalog = _load_catalog()
    r10 = [e for e in catalog if e["case"] == "r10"]
    assert len(r10) == 1
    assert r10[0]["currency"] == "XXX"


def test_r12_pampaluz_with_manual_block() -> None:
    catalog = _load_catalog()
    r12 = [e for e in catalog if e["case"] == "r12"]
    assert len(r12) == 1
    assert r12[0]["beneficiary"] == "Pampaluz Ltda"
    assert r12[0]["manual_block"] is True


def test_ids_and_invoice_numbers_unique_except_dup_exact_pairs() -> None:
    catalog = _load_catalog()
    ids = [e["id"] for e in catalog]
    assert len(ids) == len(set(ids))
    numbers = [e["invoice_number"] for e in catalog]
    dup_allowed = [n for n in numbers if n in DUP_EXACT_INVOICE_NUMBERS]
    other = [n for n in numbers if n not in DUP_EXACT_INVOICE_NUMBERS]
    assert len(other) == len(set(other))
    assert Counter(dup_allowed) == Counter({"INV-GX-DUP-EXACT": 2, "INV-H-GX-1": 2})


def test_regenerating_does_not_change_catalog_or_file_hashes() -> None:
    catalog = _load_catalog()
    catalog_bytes = CATALOG_PATH.read_bytes()
    paths = sorted(REPO_ROOT / e["path"] for e in catalog)
    hashes_before = {p: _sha256(p) for p in paths}

    subprocess.run(
        [sys.executable, str(GENERATOR_PATH)],
        check=True,
        cwd=REPO_ROOT,
    )

    assert CATALOG_PATH.read_bytes() == catalog_bytes
    for p in paths:
        assert _sha256(p) == hashes_before[p]
