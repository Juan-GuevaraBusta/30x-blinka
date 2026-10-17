"""T2.1 — Normalization for beneficiary, currency, dates, and regional amounts."""

from __future__ import annotations

from datetime import date

import pytest
from app.rules.normalize import (
    normalize_amount,
    normalize_beneficiary,
    normalize_currency,
    normalize_due_date,
    normalize_party_name,
)

ALLOWED = (
    "Globex LLC",
    "Pampaluz Ltda",
    "Rioseco Servicios SAS",
    "Norteclaro SpA",
)


def test_normalize_beneficiary_strips_suffixes_and_punctuation() -> None:
    assert normalize_beneficiary("Globex LLC") == "globex"
    assert normalize_beneficiary("GLOBEX, LLC.") == "globex"
    assert normalize_beneficiary("Pampaluz Ltda") == "pampaluz"
    assert normalize_beneficiary("Rioseco Servicios SAS") == "rioseco servicios"
    assert normalize_beneficiary("Norteclaro SpA") == "norteclaro"


def test_normalize_beneficiary_removes_accents() -> None:
    assert normalize_party_name("Ingeniería Demo S.A.") == "ingenieria demo"


def test_normalize_beneficiary_none_and_blank() -> None:
    assert normalize_beneficiary(None) is None
    assert normalize_beneficiary("   ") is None


def test_allowed_beneficiary_match_after_normalization() -> None:
    normalized_allowed = {normalize_beneficiary(name) for name in ALLOWED}
    assert normalize_beneficiary("globex llc") in normalized_allowed
    assert normalize_beneficiary("Nuevo Socio Fantasma SAS") not in normalized_allowed


def test_normalize_currency_uppercase_and_trim() -> None:
    assert normalize_currency("usd") == "USD"
    assert normalize_currency(" EUR ") == "EUR"
    assert normalize_currency("XXX") == "XXX"
    assert normalize_currency(None) is None
    assert normalize_currency("") is None


def test_normalize_due_date_iso_and_date_object() -> None:
    assert normalize_due_date("2026-01-05") == date(2026, 1, 5)
    assert normalize_due_date(date(2026, 3, 20)) == date(2026, 3, 20)
    assert normalize_due_date(None) is None
    assert normalize_due_date("not-a-date") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (800, 800.0),
        (800.5, 800.5),
        ("800", 800.0),
        ("1.000,50", 1000.5),
        ("1,000.50", 1000.5),
        ("4.200,00", 4200.0),
        ("  1 234,56  ", 1234.56),
    ],
)
def test_normalize_amount_regional_formats(raw: object, expected: float) -> None:
    result = normalize_amount(raw)
    assert result is not None
    assert abs(result - expected) < 1e-9


def test_normalize_amount_none_and_invalid() -> None:
    assert normalize_amount(None) is None
    assert normalize_amount("") is None
    assert normalize_amount("sin monto") is None
