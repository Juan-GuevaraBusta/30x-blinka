"""T2.2 — FX conversion with registered rate and date."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from app.rules.fx import convert_to_base, load_fx_table

REPO_ROOT = Path(__file__).resolve().parents[3]
FX_PATH = REPO_ROOT / "data" / "fx.json"
AS_OF = date(2026, 3, 1)


@pytest.fixture(scope="module")
def fx_table():
    return load_fx_table(FX_PATH)


def test_eur_500_converts_to_540(fx_table) -> None:
    result = convert_to_base(500, "EUR", fx_table)
    assert result.error is None
    assert result.amount_base == 540.0
    assert result.fx is not None
    assert result.fx.rate == 1.08
    assert result.fx.date == AS_OF
    assert result.currency == "EUR"


def test_cop_14_million_converts_to_3500(fx_table) -> None:
    result = convert_to_base(14_000_000, "COP", fx_table)
    assert result.error is None
    assert result.amount_base == 3500.0
    assert result.fx is not None
    assert result.fx.rate == 0.00025


def test_brl_2000_converts_to_360(fx_table) -> None:
    result = convert_to_base(2000, "BRL", fx_table)
    assert result.error is None
    assert result.amount_base == 360.0
    assert result.fx is not None
    assert result.fx.rate == 0.18


def test_usd_800_keeps_amount_and_records_identity_quote(fx_table) -> None:
    result = convert_to_base(800, "USD", fx_table)
    assert result.error is None
    assert result.amount_base == 800.0
    assert result.fx is not None
    assert result.fx.rate == 1.0
    assert result.fx.date == AS_OF
    assert result.currency == "USD"


def test_xxx_and_unknown_currency_do_not_invent_rate(fx_table) -> None:
    for code in ("XXX", "ZZZ"):
        result = convert_to_base(100, code, fx_table)
        assert result.error == "unknown_currency"
        assert result.amount_base is None
        assert result.fx is None
        assert result.currency == code


def test_missing_amount_returns_missing_amount(fx_table) -> None:
    result = convert_to_base(None, "USD", fx_table)
    assert result.error == "missing_amount"
    assert result.amount_base is None
    assert result.fx is None


def test_load_fx_table_reads_repo_data_fx_json() -> None:
    table = load_fx_table(FX_PATH)
    assert table.as_of == AS_OF
    assert table.base_currency == "USD"
    assert table.quote == "usd_per_1_unit"
    assert set(table.rates.keys()) == {"USD", "EUR", "MXN", "COP", "BRL"}
    assert "XXX" not in table.rates


def test_mxn_1000_converts_to_58(fx_table) -> None:
    result = convert_to_base(1000, "MXN", fx_table)
    assert result.error is None
    assert result.amount_base == 58.0
    assert result.fx is not None
    assert result.fx.rate == 0.058


def test_rounds_product_to_two_decimals(fx_table) -> None:
    result = convert_to_base(3, "MXN", fx_table)
    assert result.error is None
    assert result.amount_base == 0.17


def test_hold_005_cop_converts_to_2000(fx_table) -> None:
    result = convert_to_base(8_000_000, "COP", fx_table)
    assert result.error is None
    assert result.amount_base == 2000.0


def test_normalizes_currency_before_lookup(fx_table) -> None:
    result = convert_to_base(500, " eur ", fx_table)
    assert result.error is None
    assert result.amount_base == 540.0
    assert result.currency == "EUR"


def test_missing_currency_returns_missing_currency(fx_table) -> None:
    result = convert_to_base(100, None, fx_table)
    assert result.error == "missing_currency"
    assert result.amount_base is None
    assert result.fx is None


def test_string_amount_uses_normalize_amount(fx_table) -> None:
    result = convert_to_base("500", "EUR", fx_table)
    assert result.error is None
    assert result.amount_base == 540.0
