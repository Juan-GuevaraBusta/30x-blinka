"""T7.2 — Payment series per vendor (R15-R18). AI-TDD per docs/T7_2_SPEC.md.

R15-R18 only ADD severity; they must never turn a non-PAGAR decision into
PAGAR (I1), and without `payment_series` the 13/14-check list stays
byte-identical to before T7.2.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest
from app.models.domain import SEVERITY
from app.models.rules_config import PaymentSeries, RulesConfig, load_rules_config
from app.rules.checks import CHECKS, check_r14
from app.rules.context import LedgerEntry
from app.rules.decide import decide
from app.rules.fx import FxTable, load_fx_table
from app.rules.payment_series import (
    expected_periods_before,
    find_matching_series,
    paid_entries_for_series,
    period_key,
    resolve_item_key,
)
from app.rules.run_checks import run_deterministic_checks
from hypothesis import HealthCheck, given, seed, settings
from hypothesis import strategies as st
from pydantic import ValidationError
from tests.rules.test_rules_r01_r13 import make_context

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def rules() -> RulesConfig:
    return load_rules_config(REPO_ROOT / "data" / "rules.json")


@pytest.fixture(scope="module")
def fx_table() -> FxTable:
    return load_fx_table(REPO_ROOT / "data" / "fx.json")


GLOBEX_MONTHLY = {
    "id": "globex-retainer",
    "beneficiary": "Globex LLC",
    "department": "Ingenieria",
    "periodicity": "monthly",
    "currency": "USD",
    "expected_amount": {"min": 800, "max": 800},
    "start": date(2026, 1, 1),
    "end": date(2026, 3, 31),
    "total_cap": 2400,
}
CUOTASUR_INSTALLMENTS = {
    "id": "cuotasur-cuotas",
    "beneficiary": "Cuotasur SAS",
    "periodicity": "installments",
    "currency": "USD",
    "total_cap": 2000,
    "items": [
        {"key": "1/3", "due_from": date(2026, 2, 1), "due_to": date(2026, 2, 28), "amount": 1000},
        {"key": "2/3", "due_from": date(2026, 3, 1), "due_to": date(2026, 3, 31), "amount": 1000},
        {"key": "3/3", "due_from": date(2026, 4, 1), "due_to": date(2026, 4, 30), "amount": 1000},
    ],
}


def _series(payload: dict) -> PaymentSeries:
    return PaymentSeries.model_validate(payload)


def _ledger_entry(
    *,
    beneficiary: str = "Cuotasur SAS",
    amount_base: float = 1000.0,
    currency: str = "USD",
    invoice_number: str = "SEED-1",
    received_at: str = "2026-02-01T09:00:00Z",
    decision: str = "PAGAR",
    department: str | None = "Ingenieria",
    due_date: str | None = "2026-02-05",
) -> LedgerEntry:
    return LedgerEntry(
        beneficiary=beneficiary,
        amount_base=amount_base,
        currency=currency,
        invoice_number=invoice_number,
        received_at=received_at,
        decision=decision,
        department=department,
        due_date=due_date,
    )


# --- schema shape validation --------------------------------------------------------


def test_calendar_periodicity_requires_expected_amount_and_start() -> None:
    with pytest.raises(ValidationError):
        _series(
            {
                "id": "x",
                "beneficiary": "Globex LLC",
                "periodicity": "monthly",
                "currency": "USD",
            }
        )


def test_calendar_periodicity_forbids_items() -> None:
    with pytest.raises(ValidationError):
        _series(
            {
                **GLOBEX_MONTHLY,
                "items": [
                    {
                        "key": "x",
                        "due_from": date(2026, 1, 1),
                        "due_to": date(2026, 1, 2),
                        "amount": 1,
                    }
                ],
            }
        )


def test_installments_require_non_empty_items() -> None:
    with pytest.raises(ValidationError):
        _series(
            {
                "id": "x",
                "beneficiary": "Cuotasur SAS",
                "periodicity": "installments",
                "currency": "USD",
            }
        )


def test_installments_forbid_expected_amount() -> None:
    with pytest.raises(ValidationError):
        _series({**CUOTASUR_INSTALLMENTS, "expected_amount": {"min": 1, "max": 2}})


def test_items_keys_must_be_unique() -> None:
    bad_items = [dict(item, key="1/3") for item in CUOTASUR_INSTALLMENTS["items"]]
    with pytest.raises(ValidationError):
        _series({**CUOTASUR_INSTALLMENTS, "items": bad_items})


def test_default_rules_json_has_no_payment_series(rules: RulesConfig) -> None:
    assert rules.payment_series == []


# --- period_key: five periodicities, edges ------------------------------------------


def test_period_key_monthly() -> None:
    series = _series(GLOBEX_MONTHLY)
    assert period_key(series, date(2026, 1, 1)) == "2026-01"
    assert period_key(series, date(2026, 1, 31)) == "2026-01"
    assert period_key(series, date(2026, 2, 1)) == "2026-02"


def test_period_key_quarterly() -> None:
    series = _series({**GLOBEX_MONTHLY, "periodicity": "quarterly"})
    assert period_key(series, date(2026, 3, 31)) == "2026-Q1"
    assert period_key(series, date(2026, 4, 1)) == "2026-Q2"
    assert period_key(series, date(2026, 12, 31)) == "2026-Q4"
    assert period_key(series, date(2027, 1, 1)) == "2027-Q1"


def test_period_key_biweekly_blocks_from_start() -> None:
    series = _series({**GLOBEX_MONTHLY, "periodicity": "biweekly"})
    assert period_key(series, date(2026, 1, 1)) == "B0"
    assert period_key(series, date(2026, 1, 14)) == "B0"
    assert period_key(series, date(2026, 1, 15)) == "B1"
    assert period_key(series, date(2025, 12, 31)) is None  # before start


def test_period_key_installments_single_item() -> None:
    series = _series(CUOTASUR_INSTALLMENTS)
    assert period_key(series, date(2026, 3, 20)) == "2/3"
    assert period_key(series, date(2026, 1, 15)) is None  # before any item


def test_period_key_installments_ambiguous_item_is_none() -> None:
    overlapping = {
        **CUOTASUR_INSTALLMENTS,
        "items": [
            {"key": "a", "due_from": date(2026, 2, 1), "due_to": date(2026, 2, 20), "amount": 500},
            {"key": "b", "due_from": date(2026, 2, 10), "due_to": date(2026, 2, 28), "amount": 500},
        ],
    }
    series = _series(overlapping)
    key, count = resolve_item_key(series, date(2026, 2, 15))
    assert key is None
    assert count == 2
    assert period_key(series, date(2026, 2, 15)) is None


# --- find_matching_series: beneficiary + department, ambiguity --------------------


def test_find_matching_series_by_beneficiary(rules: RulesConfig, fx_table: FxTable) -> None:
    ctx = make_context(rules, fx_table, beneficiary="Globex LLC", department="Ingenieria")
    resolution = find_matching_series([_series(GLOBEX_MONTHLY)], ctx.extraction)
    assert resolution.series is not None
    assert resolution.series.id == "globex-retainer"
    assert resolution.ambiguous is False


def test_find_matching_series_no_match_is_not_an_error(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    ctx = make_context(rules, fx_table, beneficiary="Initech SAS")
    resolution = find_matching_series([_series(GLOBEX_MONTHLY)], ctx.extraction)
    assert resolution.series is None
    assert resolution.ambiguous is False


def test_find_matching_series_department_mismatch_is_no_match(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    ctx = make_context(rules, fx_table, beneficiary="Globex LLC", department="Marketing")
    resolution = find_matching_series([_series(GLOBEX_MONTHLY)], ctx.extraction)
    assert resolution.series is None


def test_find_matching_series_two_series_same_beneficiary_is_ambiguous(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    other = {**GLOBEX_MONTHLY, "id": "globex-second", "department": None}
    ctx = make_context(rules, fx_table, beneficiary="Globex LLC", department="Ingenieria")
    resolution = find_matching_series([_series(GLOBEX_MONTHLY), _series(other)], ctx.extraction)
    assert resolution.series is None
    assert resolution.ambiguous is True


# --- paid_entries_for_series + expected_periods_before ------------------------------


def test_paid_entries_for_series_filters_by_beneficiary_and_department() -> None:
    series = _series(GLOBEX_MONTHLY)
    entries = (
        _ledger_entry(beneficiary="Globex LLC", department="Ingenieria"),
        _ledger_entry(beneficiary="Globex LLC", department="Marketing"),
        _ledger_entry(beneficiary="Initech SAS", department="Ingenieria"),
        _ledger_entry(beneficiary="Globex LLC", department="Ingenieria", decision="ESCALAR"),
    )
    paid = paid_entries_for_series(entries, series)
    assert len(paid) == 1
    assert paid[0].department == "Ingenieria"


def test_expected_periods_before_monthly_skips_gap() -> None:
    series = _series(GLOBEX_MONTHLY)
    assert expected_periods_before(series, date(2026, 1, 20)) == []
    assert expected_periods_before(series, date(2026, 3, 5)) == ["2026-01", "2026-02"]


def test_expected_periods_before_installments_is_empty() -> None:
    series = _series(CUOTASUR_INSTALLMENTS)
    assert expected_periods_before(series, date(2026, 3, 20)) == []


# --- checks R15-R18 composed through run_deterministic_checks ---------------------


def test_run_deterministic_checks_without_series_is_unchanged(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    assert rules.payment_series == []
    ctx = make_context(rules, fx_table)
    results = run_deterministic_checks(ctx)
    assert len(results) == len(CHECKS) == 13
    assert all(r.rule not in ("R15", "R16", "R17", "R18") for r in results)


def test_invoice_for_unrelated_beneficiary_does_not_emit_series_rules(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    policy_rules = rules.model_copy(update={"payment_series": [_series(GLOBEX_MONTHLY)]})
    ctx = make_context(policy_rules, fx_table, beneficiary="Initech SAS")
    results = run_deterministic_checks(ctx)
    assert all(r.rule not in ("R15", "R16", "R17", "R18") for r in results)


def test_in_window_correct_amount_is_pagar(rules: RulesConfig, fx_table: FxTable) -> None:
    policy_rules = rules.model_copy(update={"payment_series": [_series(GLOBEX_MONTHLY)]})
    ctx = make_context(
        policy_rules,
        fx_table,
        beneficiary="Globex LLC",
        department="Ingenieria",
        amount=800.0,
        amount_base=800.0,
        fee_amount=800.0,
        due_date="2026-01-20",
    )
    checks = run_deterministic_checks(ctx)
    by_rule = {c.rule: c for c in checks}
    assert by_rule["R15"].result == "OK"
    assert by_rule["R16"].result == "OK"
    assert by_rule["R17"].result == "OK"
    assert by_rule["R18"].result == "OK"
    assert decide(checks) == "PAGAR"


def test_due_date_after_end_is_r15_escalar(rules: RulesConfig, fx_table: FxTable) -> None:
    policy_rules = rules.model_copy(update={"payment_series": [_series(GLOBEX_MONTHLY)]})
    ctx = make_context(
        policy_rules,
        fx_table,
        beneficiary="Globex LLC",
        department="Ingenieria",
        amount=800.0,
        amount_base=800.0,
        fee_amount=800.0,
        due_date="2026-04-15",
    )
    checks = run_deterministic_checks(ctx)
    r15 = next(c for c in checks if c.rule == "R15")
    assert r15.result == "FALLA"
    assert r15.on_fail == "ESCALAR"
    assert decide(checks) == "ESCALAR"


def test_amount_out_of_range_is_r15_escalar(rules: RulesConfig, fx_table: FxTable) -> None:
    policy_rules = rules.model_copy(update={"payment_series": [_series(GLOBEX_MONTHLY)]})
    ctx = make_context(
        policy_rules,
        fx_table,
        beneficiary="Globex LLC",
        department="Ingenieria",
        amount=1200.0,
        amount_base=1200.0,
        fee_amount=800.0,
        due_date="2026-02-10",
    )
    checks = run_deterministic_checks(ctx)
    r15 = next(c for c in checks if c.rule == "R15")
    assert r15.result == "FALLA"


def test_duplicate_period_different_invoice_number_is_r16_frenar(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    policy_rules = rules.model_copy(update={"payment_series": [_series(CUOTASUR_INSTALLMENTS)]})
    seed = _ledger_entry(
        invoice_number="INV-SEED-2",
        received_at="2026-03-01T09:00:00Z",
        due_date="2026-03-05",
    )
    ctx = make_context(
        policy_rules,
        fx_table,
        beneficiary="Cuotasur SAS",
        department="Ingenieria",
        amount=1000.0,
        amount_base=1000.0,
        fee_amount=1000.0,
        invoice_number="INV-NEW",
        due_date="2026-03-10",
        ledger=(seed,),
    )
    checks = run_deterministic_checks(ctx)
    r16 = next(c for c in checks if c.rule == "R16")
    assert r16.result == "FALLA"
    assert r16.on_fail == "FRENAR"
    assert decide(checks) == "FRENAR"


def test_ledger_row_without_due_date_makes_r16_indeterminate(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    policy_rules = rules.model_copy(update={"payment_series": [_series(CUOTASUR_INSTALLMENTS)]})
    seed = _ledger_entry(invoice_number="INV-SEED-NO-DATE", due_date=None)
    ctx = make_context(
        policy_rules,
        fx_table,
        beneficiary="Cuotasur SAS",
        department="Ingenieria",
        amount=1000.0,
        amount_base=1000.0,
        fee_amount=1000.0,
        invoice_number="INV-NEW",
        due_date="2026-03-10",
        ledger=(seed,),
    )
    checks = run_deterministic_checks(ctx)
    r16 = next(c for c in checks if c.rule == "R16")
    assert r16.result == "INDETERMINADO"
    assert decide(checks) in ("ESCALAR", "FRENAR")


def test_total_cap_exceeded_is_r17_frenar(rules: RulesConfig, fx_table: FxTable) -> None:
    policy_rules = rules.model_copy(update={"payment_series": [_series(CUOTASUR_INSTALLMENTS)]})
    seed1 = _ledger_entry(
        invoice_number="INV-SEED-1", received_at="2026-02-01T09:00:00Z", due_date="2026-02-05"
    )
    seed2 = _ledger_entry(
        invoice_number="INV-SEED-2", received_at="2026-03-01T09:00:00Z", due_date="2026-03-05"
    )
    ctx = make_context(
        policy_rules,
        fx_table,
        beneficiary="Cuotasur SAS",
        department="Ingenieria",
        amount=1000.0,
        amount_base=1000.0,
        fee_amount=1000.0,
        invoice_number="INV-NEW",
        due_date="2026-04-10",
        ledger=(seed1, seed2),
    )
    checks = run_deterministic_checks(ctx)
    r16 = next(c for c in checks if c.rule == "R16")
    r17 = next(c for c in checks if c.rule == "R17")
    assert r16.result == "OK"  # different period (3/3), not a duplicate
    assert r17.result == "FALLA"
    assert r17.on_fail == "FRENAR"
    assert decide(checks) == "FRENAR"


def test_r15_series_currency_differs_from_base_is_indeterminate(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    """Bug: `series.currency` was declared but never checked against the base
    currency that `amount_base` is always expressed in. A series pactated in a
    non-base currency must fail closed instead of comparing raw numbers across
    currencies."""
    eur_series = _series({**GLOBEX_MONTHLY, "currency": "EUR"})
    policy_rules = rules.model_copy(update={"payment_series": [eur_series]})
    ctx = make_context(
        policy_rules,
        fx_table,
        beneficiary="Globex LLC",
        department="Ingenieria",
        amount=800.0,
        amount_base=800.0,
        fee_amount=800.0,
        due_date="2026-01-20",
    )
    checks = run_deterministic_checks(ctx)
    r15 = next(c for c in checks if c.rule == "R15")
    assert r15.result == "INDETERMINADO"
    assert decide(checks) == "ESCALAR"


def test_r17_series_currency_differs_from_base_is_indeterminate(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    eur_series = _series({**CUOTASUR_INSTALLMENTS, "currency": "EUR"})
    policy_rules = rules.model_copy(update={"payment_series": [eur_series]})
    ctx = make_context(
        policy_rules,
        fx_table,
        beneficiary="Cuotasur SAS",
        department="Ingenieria",
        amount=1000.0,
        amount_base=1000.0,
        fee_amount=1000.0,
        due_date="2026-02-10",
    )
    checks = run_deterministic_checks(ctx)
    r17 = next(c for c in checks if c.rule == "R17")
    assert r17.result == "INDETERMINADO"


def test_r15_installment_amount_within_half_cent_tolerance_is_ok(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    """Bug: exact float equality on installment amounts. A 0.4-cent rounding
    drift (well within the 0.005 base-currency tolerance) must still match."""
    policy_rules = rules.model_copy(update={"payment_series": [_series(CUOTASUR_INSTALLMENTS)]})
    ctx = make_context(
        policy_rules,
        fx_table,
        beneficiary="Cuotasur SAS",
        department="Ingenieria",
        amount=999.996,
        amount_base=999.996,
        fee_amount=999.996,
        due_date="2026-02-10",
    )
    checks = run_deterministic_checks(ctx)
    r15 = next(c for c in checks if c.rule == "R15")
    assert r15.result == "OK"


def test_r15_installment_amount_beyond_tolerance_still_fails(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    policy_rules = rules.model_copy(update={"payment_series": [_series(CUOTASUR_INSTALLMENTS)]})
    ctx = make_context(
        policy_rules,
        fx_table,
        beneficiary="Cuotasur SAS",
        department="Ingenieria",
        amount=990.0,
        amount_base=990.0,
        fee_amount=990.0,
        due_date="2026-02-10",
    )
    checks = run_deterministic_checks(ctx)
    r15 = next(c for c in checks if c.rule == "R15")
    assert r15.result == "FALLA"


def test_r16_malformed_ledger_due_date_is_indeterminate_not_a_crash(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    """Bug: a legacy ledger row with an unparseable due_date made `check_r16`
    raise `ValueError` from `date.fromisoformat`. It must fail closed instead."""
    policy_rules = rules.model_copy(update={"payment_series": [_series(CUOTASUR_INSTALLMENTS)]})
    seed = _ledger_entry(invoice_number="INV-SEED-LEGACY", due_date="not-a-date")
    ctx = make_context(
        policy_rules,
        fx_table,
        beneficiary="Cuotasur SAS",
        department="Ingenieria",
        amount=1000.0,
        amount_base=1000.0,
        fee_amount=1000.0,
        invoice_number="INV-NEW",
        due_date="2026-02-10",
        ledger=(seed,),
    )
    checks = run_deterministic_checks(ctx)
    r16 = next(c for c in checks if c.rule == "R16")
    assert r16.result == "INDETERMINADO"
    assert decide(checks) in ("ESCALAR", "FRENAR")


def test_r18_malformed_ledger_due_date_does_not_crash(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    """R18 is purely informational (never FALLA/INDETERMINADO); a malformed
    legacy due_date must be skipped, not raise."""
    policy_rules = rules.model_copy(update={"payment_series": [_series(GLOBEX_MONTHLY)]})
    seed = _ledger_entry(
        beneficiary="Globex LLC",
        invoice_number="INV-SEED-LEGACY",
        due_date="not-a-date",
    )
    ctx = make_context(
        policy_rules,
        fx_table,
        beneficiary="Globex LLC",
        department="Ingenieria",
        amount=800.0,
        amount_base=800.0,
        fee_amount=800.0,
        due_date="2026-03-05",
        ledger=(seed,),
    )
    checks = run_deterministic_checks(ctx)
    r18 = next(c for c in checks if c.rule == "R18")
    assert r18.result == "OK"


def test_r17_reprocessing_same_invoice_does_not_double_count(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    """Bug: re-sending the same invoice (already counted in the ledger) was
    added to `total_paid` a second time, overstating the series total."""
    policy_rules = rules.model_copy(update={"payment_series": [_series(CUOTASUR_INSTALLMENTS)]})
    seed = _ledger_entry(
        invoice_number="INV-REPROCESS",
        amount_base=2000.0,
        received_at="2026-02-01T09:00:00Z",
        due_date="2026-02-05",
    )
    ctx = make_context(
        policy_rules,
        fx_table,
        beneficiary="Cuotasur SAS",
        department="Ingenieria",
        amount=2000.0,
        amount_base=2000.0,
        fee_amount=2000.0,
        invoice_number="INV-REPROCESS",
        due_date="2026-02-05",
        ledger=(seed,),
    )
    checks = run_deterministic_checks(ctx)
    r17 = next(c for c in checks if c.rule == "R17")
    assert r17.result == "OK"


def test_skipped_period_is_r18_informational_without_changing_decision(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    policy_rules = rules.model_copy(update={"payment_series": [_series(GLOBEX_MONTHLY)]})
    ctx = make_context(
        policy_rules,
        fx_table,
        beneficiary="Globex LLC",
        department="Ingenieria",
        amount=800.0,
        amount_base=800.0,
        fee_amount=800.0,
        due_date="2026-03-05",
    )
    checks = run_deterministic_checks(ctx)
    r18 = next(c for c in checks if c.rule == "R18")
    assert r18.result == "OK"
    assert "2026-01" in r18.detail
    assert "2026-02" in r18.detail
    assert decide(checks) == "PAGAR"


# --- property test: payment_series only ever raises severity -----------------------

_BENEFICIARIES = ("Globex LLC", "Initech SAS")
_PERIODICITIES = ("monthly", "quarterly", "biweekly", "installments", "milestones")
_DEPARTMENTS = ("Ingenieria", "Marketing")
_TOTAL_CAP = st.one_of(st.none(), st.floats(min_value=1, max_value=50_000, allow_nan=False))


@st.composite
def _calendar_series_payload(draw: st.DrawFn, *, sid: str, beneficiary: str) -> dict:
    periodicity = draw(st.sampled_from(("monthly", "quarterly", "biweekly")))
    start = draw(st.dates(min_value=date(2025, 1, 1), max_value=date(2026, 6, 1)))
    end = draw(
        st.one_of(st.none(), st.dates(min_value=start, max_value=date(2027, 12, 31)))
    )
    lo = draw(st.floats(min_value=1, max_value=5000, allow_nan=False))
    hi = lo + draw(st.floats(min_value=0, max_value=1000, allow_nan=False))
    total_cap = draw(_TOTAL_CAP)
    department = draw(st.one_of(st.none(), st.sampled_from(_DEPARTMENTS)))
    return {
        "id": sid,
        "beneficiary": beneficiary,
        "department": department,
        "periodicity": periodicity,
        "currency": "USD",
        "expected_amount": {"min": lo, "max": hi},
        "start": start,
        "end": end,
        "total_cap": total_cap,
    }


@st.composite
def _installment_series_payload(draw: st.DrawFn, *, sid: str, beneficiary: str) -> dict:
    periodicity = draw(st.sampled_from(("installments", "milestones")))
    n = draw(st.integers(min_value=1, max_value=3))
    cursor = draw(st.dates(min_value=date(2025, 1, 1), max_value=date(2026, 1, 1)))
    items = []
    for i in range(n):
        length = draw(st.integers(min_value=1, max_value=30))
        due_to = cursor + timedelta(days=length)
        amount = draw(st.floats(min_value=1, max_value=5000, allow_nan=False))
        items.append(
            {"key": f"{i + 1}/{n}", "due_from": cursor, "due_to": due_to, "amount": amount}
        )
        cursor = due_to + timedelta(days=1)
    total_cap = draw(_TOTAL_CAP)
    department = draw(st.one_of(st.none(), st.sampled_from(_DEPARTMENTS)))
    return {
        "id": sid,
        "beneficiary": beneficiary,
        "department": department,
        "periodicity": periodicity,
        "currency": "USD",
        "items": items,
        "total_cap": total_cap,
    }


@st.composite
def _series_list_payload(draw: st.DrawFn) -> tuple[list[dict], str]:
    beneficiary = draw(st.sampled_from(_BENEFICIARIES))
    n = draw(st.integers(min_value=0, max_value=2))
    series = []
    for i in range(n):
        kind = draw(st.sampled_from(("calendar", "installments")))
        payload = draw(
            _calendar_series_payload(sid=f"s{i}", beneficiary=beneficiary)
            if kind == "calendar"
            else _installment_series_payload(sid=f"s{i}", beneficiary=beneficiary)
        )
        series.append(payload)
    return series, beneficiary


@st.composite
def _maybe_ledger_entry(draw: st.DrawFn, *, beneficiary: str) -> LedgerEntry | None:
    if not draw(st.booleans()):
        return None
    has_due_date = draw(st.booleans())
    due_date = (
        draw(st.dates(min_value=date(2025, 1, 1), max_value=date(2027, 12, 31))).isoformat()
        if has_due_date
        else None
    )
    return LedgerEntry(
        beneficiary=beneficiary,
        amount_base=draw(st.floats(min_value=1, max_value=5000, allow_nan=False)),
        currency="USD",
        invoice_number=draw(st.text(alphabet="ABCDEFGH0123456789", min_size=3, max_size=8)),
        received_at="2026-01-05T09:00:00Z",
        decision="PAGAR",
        department=draw(st.one_of(st.none(), st.sampled_from(("Ingenieria", "Marketing")))),
        due_date=due_date,
    )


@seed(20261017)
@settings(max_examples=500, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    series_and_beneficiary=_series_list_payload(),
    amount_base=st.one_of(st.none(), st.floats(min_value=0, max_value=20_000, allow_nan=False)),
    due_date=st.one_of(
        st.none(), st.dates(min_value=date(2024, 1, 1), max_value=date(2028, 12, 31))
    ),
    department=st.one_of(st.none(), st.sampled_from(("Ingenieria", "Marketing"))),
    seed_entry=_maybe_ledger_entry(beneficiary="Globex LLC"),
)
def test_applying_any_payment_series_never_lowers_severity(
    series_and_beneficiary: tuple[list[dict], str],
    amount_base: float | None,
    due_date: date | None,
    department: str | None,
    seed_entry: LedgerEntry | None,
) -> None:
    series_payloads, beneficiary = series_and_beneficiary
    rules = load_rules_config(REPO_ROOT / "data" / "rules.json")
    fx_table = load_fx_table(REPO_ROOT / "data" / "fx.json")
    series = [PaymentSeries.model_validate(payload) for payload in series_payloads]
    policy_rules = rules.model_copy(update={"payment_series": series})

    ledger = (seed_entry,) if seed_entry is not None else ()
    ctx_base = make_context(
        rules,
        fx_table,
        beneficiary=beneficiary,
        amount=amount_base,
        amount_base=amount_base,
        fee_amount=amount_base if amount_base is not None else 800.0,
        department=department,
        due_date=due_date.isoformat() if due_date else None,
        ledger=ledger,
    )
    ctx_policy = replace(ctx_base, rules=policy_rules)

    decision_base = decide(run_deterministic_checks(ctx_base))
    decision_policy = decide(run_deterministic_checks(ctx_policy))

    assert SEVERITY[decision_policy] >= SEVERITY[decision_base]
    if decision_base != "PAGAR":
        assert decision_policy != "PAGAR"


@seed(20261017)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    policy_payload=st.fixed_dictionaries(
        {
            "routes": st.just(
                [{"id": "default", "match": {}, "require": {"mode": "auto"}}]
            )
        }
    ),
    series_and_beneficiary=_series_list_payload(),
    amount_base=st.one_of(st.none(), st.floats(min_value=0, max_value=20_000, allow_nan=False)),
)
def test_combining_approval_policy_and_payment_series_still_only_raises_severity(
    policy_payload: dict,
    series_and_beneficiary: tuple[list[dict], str],
    amount_base: float | None,
) -> None:
    """Cross-feature sanity: T7.1's R14 and T7.2's R15-R18 compose (both append-only)."""
    from app.models.rules_config import ApprovalPolicy

    series_payloads, beneficiary = series_and_beneficiary
    rules = load_rules_config(REPO_ROOT / "data" / "rules.json")
    fx_table = load_fx_table(REPO_ROOT / "data" / "fx.json")
    series = [PaymentSeries.model_validate(payload) for payload in series_payloads]
    policy = ApprovalPolicy.model_validate(policy_payload)
    both_rules = rules.model_copy(
        update={"approval_policy": policy, "payment_series": series}
    )

    ctx_base = make_context(
        rules,
        fx_table,
        beneficiary=beneficiary,
        amount=amount_base,
        amount_base=amount_base,
        fee_amount=amount_base if amount_base is not None else 800.0,
    )
    ctx_both = replace(ctx_base, rules=both_rules)

    decision_base = decide(run_deterministic_checks(ctx_base))
    decision_both = decide(run_deterministic_checks(ctx_both))

    assert SEVERITY[decision_both] >= SEVERITY[decision_base]
    assert check_r14 is not None  # keep the T7.1 import meaningful/used
