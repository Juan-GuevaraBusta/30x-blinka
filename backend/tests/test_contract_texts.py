"""T1.4 — Structural checks for synthetic provider contract texts."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "data" / "contracts"
COMPANY_PATH = REPO_ROOT / "data" / "company.json"

EXPECTED_CONTRACT_FILES: frozenset[str] = frozenset(
    {
        "globex-llc.txt",
        "initech-sas.txt",
        "norteclaro-spa.txt",
        "andesbyte-sas.txt",
        "pampaluz-ltda.txt",
        "rioseco-servicios-sas.txt",
        "luma-austral-sa.txt",
    }
)

BENEFICIARY_TO_FILE: dict[str, str] = {
    "Globex LLC": "globex-llc.txt",
    "Initech SAS": "initech-sas.txt",
    "Norteclaro SpA": "norteclaro-spa.txt",
    "Andesbyte SAS": "andesbyte-sas.txt",
    "Pampaluz Ltda": "pampaluz-ltda.txt",
    "Rioseco Servicios SAS": "rioseco-servicios-sas.txt",
    "Luma Austral SA": "luma-austral-sa.txt",
}

R01_OUTSIDE_NAMES = ("Nuevo Socio Fantasma SAS", "Taller Sin Alta Ltda")
CLAUSE_LINE = re.compile(r"^\d+\.\d+ ")


def _allowed_beneficiaries() -> list[str]:
    data = json.loads(COMPANY_PATH.read_text(encoding="utf-8"))
    return list(data["allowed_beneficiaries"])


def test_contract_directory_has_exactly_seven_text_files() -> None:
    assert CONTRACTS_DIR.is_dir()
    names = {p.name for p in CONTRACTS_DIR.glob("*.txt")}
    assert names == set(EXPECTED_CONTRACT_FILES)


def test_each_allowed_beneficiary_has_one_contract_file() -> None:
    allowed = _allowed_beneficiaries()
    assert set(allowed) == set(BENEFICIARY_TO_FILE)
    found: set[str] = set()
    for name in allowed:
        path = CONTRACTS_DIR / BENEFICIARY_TO_FILE[name]
        assert path.is_file(), f"Missing contract for {name}: {path}"
        text = path.read_text(encoding="utf-8")
        marker = f"El beneficiario autorizado es {name}."
        assert text.count(marker) == 1
        found.add(name)
    assert found == set(allowed)


def test_confirmed_false_on_all_contracts() -> None:
    for filename in EXPECTED_CONTRACT_FILES:
        text = (CONTRACTS_DIR / filename).read_text(encoding="utf-8")
        assert "confirmed: false" in text
        assert "confirmed: true" not in text


def test_numbered_subclauses_present() -> None:
    for filename in EXPECTED_CONTRACT_FILES:
        text = (CONTRACTS_DIR / filename).read_text(encoding="utf-8")
        assert any(CLAUSE_LINE.match(line) for line in text.splitlines())


def test_clear_contracts_have_single_pactada_tariff_line() -> None:
    for filename in EXPECTED_CONTRACT_FILES:
        if filename == "initech-sas.txt":
            continue
        text = (CONTRACTS_DIR / filename).read_text(encoding="utf-8")
        assert text.count("La tarifa pactada es ") == 1


def test_initech_ambiguous_tariff_clauses() -> None:
    text = (CONTRACTS_DIR / "initech-sas.txt").read_text(encoding="utf-8")
    assert "1200 USD" in text
    assert "1800 USD" in text
    assert "no define si el servicio incluye soporte prioritario" in text
    assert "La tarifa pactada es" not in text


def test_no_r01_outside_beneficiary_names_in_contracts() -> None:
    for filename in EXPECTED_CONTRACT_FILES:
        text = (CONTRACTS_DIR / filename).read_text(encoding="utf-8")
        for outside in R01_OUTSIDE_NAMES:
            assert outside not in text


def test_required_terms_in_every_contract() -> None:
    required = (
        "2026-01-01",
        "2026-12-31",
        "mensual",
        "El tope por periodo mensual es",
        "La moneda del contrato es",
    )
    for filename in EXPECTED_CONTRACT_FILES:
        text = (CONTRACTS_DIR / filename).read_text(encoding="utf-8")
        for fragment in required:
            assert fragment in text, f"{filename} missing {fragment}"
