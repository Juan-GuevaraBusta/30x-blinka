"""T9.1 (D061) — `compile_rules` shapes, conflicts, R06 fixed-amount, and the
mandatory severity property test.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from app.models.agreement import (
    HourlyAgreement,
    InstallmentsAgreement,
    RetainerAgreement,
    UnitPricingAgreement,
)
from app.models.domain import SEVERITY
from app.models.metered import MeteredLine
from app.models.rules_config import (
    AmountRange,
    PaymentSeries,
    RulesConfig,
    TieredFormula,
    TieredTier,
    UnitRateFormula,
    VendorOnboarding,
    load_rules_config,
)
from app.rules.agreements import (
    ActiveAgreement,
    AgreementConflictError,
    agreement_contract_map,
    agreement_ref_id,
    compile_rules,
    contract_terms_for_agreement,
)
from app.rules.checks import check_r19
from app.rules.decide import decide
from app.rules.fx import FxTable, load_fx_table
from app.rules.run_checks import run_deterministic_checks
from app.rules.variable_pricing import find_pricing_terms
from hypothesis import HealthCheck, given, seed, settings
from hypothesis import strategies as st
from tests.rules.test_rules_r01_r13 import make_context

REPO_ROOT = Path(__file__).resolve().parents[3]
RULES_PATH = REPO_ROOT / "data" / "rules.json"
F7_RULES_PATH = REPO_ROOT / "data" / "f7" / "rules.json"


@pytest.fixture
def base_rules() -> RulesConfig:
    return load_rules_config(RULES_PATH)


@pytest.fixture(scope="module")
def f7_rules() -> RulesConfig:
    return load_rules_config(F7_RULES_PATH)


@pytest.fixture(scope="module")
def fx_table() -> FxTable:
    return load_fx_table(REPO_ROOT / "data" / "fx.json")


def _retainer(**overrides: object) -> RetainerAgreement:
    payload: dict[str, object] = {
        "vendor_name": "Globex LLC",
        "department": "Ingenieria",
        "currency": "USD",
        "periodicity": "monthly",
        "amount": {"min": 800, "max": 800},
        "valid_from": date(2026, 1, 1),
        "valid_to": date(2026, 3, 31),
        "total_cap": 2400,
    }
    payload.update(overrides)
    return RetainerAgreement.model_validate(payload)


def _installments(**overrides: object) -> InstallmentsAgreement:
    payload: dict[str, object] = {
        "vendor_name": "Luma Austral SA",
        "currency": "USD",
        "kind": "installments",
        "valid_from": date(2026, 2, 1),
        "total_cap": 2000,
        "items": [
            {"key": "1/3", "due_from": "2026-02-01", "due_to": "2026-02-28", "amount": 1000},
            {"key": "2/3", "due_from": "2026-03-01", "due_to": "2026-03-31", "amount": 1000},
            {"key": "3/3", "due_from": "2026-04-01", "due_to": "2026-04-30", "amount": 1000},
        ],
    }
    payload.update(overrides)
    return InstallmentsAgreement.model_validate(payload)


def _hourly(**overrides: object) -> HourlyAgreement:
    payload: dict[str, object] = {
        "vendor_name": "Andesbyte SAS",
        "currency": "USD",
        "valid_from": date(2026, 1, 1),
        "rate": 25,
        "included_hours": 120,
        "overtime": {"multiplier": 1.5},
    }
    payload.update(overrides)
    return HourlyAgreement.model_validate(payload)


def _unit_pricing(**overrides: object) -> UnitPricingAgreement:
    payload: dict[str, object] = {
        "vendor_name": "Pampaluz Ltda",
        "currency": "USD",
        "valid_from": date(2026, 1, 1),
        "formula": {
            "kind": "tiered",
            "unit": "unidad",
            "tiers": [{"up_to": 100, "rate": 10}, {"up_to": None, "rate": 8}],
        },
    }
    payload.update(overrides)
    return UnitPricingAgreement.model_validate(payload)


def _active(agreement, *, version: int = 1, confirmed_by: str = "cfo@demo.test") -> ActiveAgreement:
    return ActiveAgreement(agreement=agreement, version=version, confirmed_by=confirmed_by)


# --- §4 fixed shapes, matching data/f7/rules.json ---------------------------------


def test_retainer_compiles_to_payment_series_shape(base_rules: RulesConfig) -> None:
    compiled = compile_rules(base_rules, [_active(_retainer())])
    f7 = load_rules_config(F7_RULES_PATH)
    f7_series = next(s for s in f7.payment_series if s.id == "globex-retainer")

    series = next(s for s in compiled.rules.payment_series if s.beneficiary == "Globex LLC")
    assert series.id == agreement_ref_id("globex", 1)
    assert series.model_dump(exclude={"id"}) == f7_series.model_dump(exclude={"id"})
    assert compiled.provenance["payment_series:globex"] == series.id


def test_installments_compiles_to_payment_series_shape(base_rules: RulesConfig) -> None:
    compiled = compile_rules(base_rules, [_active(_installments())])
    f7 = load_rules_config(F7_RULES_PATH)
    f7_series = next(s for s in f7.payment_series if s.id == "cuotasur-cuotas")

    series = next(s for s in compiled.rules.payment_series if s.beneficiary == "Luma Austral SA")
    assert series.model_dump(exclude={"id", "beneficiary"}) == f7_series.model_dump(
        exclude={"id", "beneficiary"}
    )


def test_unit_pricing_tiered_matches_f7_shape(base_rules: RulesConfig) -> None:
    compiled = compile_rules(base_rules, [_active(_unit_pricing())])
    f7 = load_rules_config(F7_RULES_PATH)
    f7_terms = next(p for p in f7.variable_pricing if p.beneficiary == "Pampaluz Ltda")

    terms = next(p for p in compiled.rules.variable_pricing if p.beneficiary == "Pampaluz Ltda")
    assert terms.formula == f7_terms.formula
    assert terms.currency == f7_terms.currency


def test_unit_pricing_unit_rate_with_cap(base_rules: RulesConfig) -> None:
    agreement = _unit_pricing(
        vendor_name="Andesbyte SAS",
        formula={"kind": "unit_rate", "unit": "hora", "rate": 50},
        period_cap=6000,
    )
    compiled = compile_rules(base_rules, [_active(agreement)])
    terms = next(p for p in compiled.rules.variable_pricing if p.beneficiary == "Andesbyte SAS")
    assert terms.formula == UnitRateFormula(kind="unit_rate", unit="hora", rate=50, cap=6000)


def test_hourly_without_overtime_is_unit_rate(base_rules: RulesConfig) -> None:
    agreement = _hourly(overtime=None, period_cap=6000)
    compiled = compile_rules(base_rules, [_active(agreement)])
    terms = next(p for p in compiled.rules.variable_pricing if p.beneficiary == "Andesbyte SAS")
    assert terms.formula == UnitRateFormula(kind="unit_rate", unit="hora", rate=25, cap=6000)


def test_hourly_with_overtime_is_tiered_with_combined_cap(base_rules: RulesConfig) -> None:
    agreement = _hourly(overtime={"multiplier": 1.5, "max_hours": 40}, period_cap=100000)
    compiled = compile_rules(base_rules, [_active(agreement)])
    terms = next(p for p in compiled.rules.variable_pricing if p.beneficiary == "Andesbyte SAS")
    # Tope = min(period_cap, included*rate + max_hours*rate*multiplier)
    expected_cap = min(100000, 120 * 25 + 40 * 25 * 1.5)
    assert terms.formula == TieredFormula(
        kind="tiered",
        unit="hora",
        tiers=[TieredTier(up_to=120, rate=25), TieredTier(up_to=None, rate=37.5)],
        cap=expected_cap,
    )


def test_new_vendor_added_to_allowlist_and_vendor_additions(base_rules: RulesConfig) -> None:
    agreement = _hourly(vendor_name="Brand New Vendor LLC")
    compiled = compile_rules(base_rules, [_active(agreement, confirmed_by="cfo@demo.test")])
    assert "Brand New Vendor LLC" in compiled.rules.allowed_beneficiaries
    additions = compiled.rules.vendor_additions
    addition = next(a for a in additions if a.beneficiary == "Brand New Vendor LLC")
    assert addition.added_by == "cfo@demo.test"
    assert compiled.rules.vendor_onboarding == VendorOnboarding(
        enabled=True, first_invoice_requires_approval=True
    )


def test_already_allowed_vendor_not_added_twice(base_rules: RulesConfig) -> None:
    compiled = compile_rules(base_rules, [_active(_retainer())])
    assert compiled.rules.allowed_beneficiaries.count("Globex LLC") == 1
    assert compiled.rules.vendor_additions == []
    assert compiled.rules.vendor_onboarding is None


# --- §4 conflict and no-agreements equality ---------------------------------------


def test_conflict_with_hand_written_payment_series_raises(base_rules: RulesConfig) -> None:
    hand_written = base_rules.model_copy(
        update={
            "payment_series": [
                PaymentSeries(
                    id="manual-globex",
                    beneficiary="Globex LLC",
                    periodicity="monthly",
                    currency="USD",
                    expected_amount=AmountRange(min=800, max=800),
                    start=date(2026, 1, 1),
                )
            ]
        }
    )
    with pytest.raises(AgreementConflictError):
        compile_rules(hand_written, [_active(_retainer())])


def test_conflict_with_hand_written_variable_pricing_raises(base_rules: RulesConfig) -> None:
    from app.models.rules_config import PricingTerms

    hand_written = base_rules.model_copy(
        update={
            "variable_pricing": [
                PricingTerms(
                    beneficiary="Andesbyte SAS",
                    currency="USD",
                    contract_clause="manual",
                    formula=UnitRateFormula(kind="unit_rate", unit="hora", rate=10),
                )
            ]
        }
    )
    with pytest.raises(AgreementConflictError):
        compile_rules(hand_written, [_active(_hourly())])


def test_no_agreements_equals_base(base_rules: RulesConfig) -> None:
    compiled = compile_rules(base_rules, [])
    assert compiled.rules == base_rules
    assert compiled.rules.model_dump(mode="json") == base_rules.model_dump(mode="json")
    assert compiled.provenance == {}


# --- §4 R06 single fixed amount ----------------------------------------------------


def test_retainer_with_min_eq_max_yields_contract_terms() -> None:
    terms = contract_terms_for_agreement(_retainer())
    assert terms is not None
    assert terms.fee_amount == 800
    assert terms.fee_currency == "USD"


def test_retainer_with_range_yields_no_contract_terms() -> None:
    agreement = _retainer(amount={"min": 700, "max": 900})
    assert contract_terms_for_agreement(agreement) is None


def test_installments_with_unequal_amounts_yields_no_contract_terms() -> None:
    agreement = _installments(
        items=[
            {"key": "1/2", "due_from": "2026-02-01", "due_to": "2026-02-28", "amount": 1000},
            {"key": "2/2", "due_from": "2026-03-01", "due_to": "2026-03-31", "amount": 1500},
        ]
    )
    assert contract_terms_for_agreement(agreement) is None


def test_hourly_yields_no_contract_terms() -> None:
    assert contract_terms_for_agreement(_hourly()) is None


def test_agreement_contract_map_only_includes_fixed_amount() -> None:
    mapping = agreement_contract_map([_active(_retainer()), _active(_hourly(), version=1)])
    assert "globex" in mapping
    assert "andesbyte sas" not in mapping


# --- §4 criterion 2: hours with overtime, exact numeric example -------------------


def test_hourly_overtime_overbill_is_frenar(base_rules: RulesConfig, fx_table: FxTable) -> None:
    agreement = _hourly()  # 120h @ 25, x1.5 overtime
    compiled = compile_rules(base_rules, [_active(agreement)])
    terms = next(p for p in compiled.rules.variable_pricing if p.beneficiary == "Andesbyte SAS")

    lines = (MeteredLine(quantity=128, unit="hora", source_span="128 horas"),)
    ctx = make_context(
        compiled.rules,
        fx_table,
        beneficiary="Andesbyte SAS",
        amount=3600,
        amount_base=3600.0,
        doc_text="128 horas",
    )
    ctx = replace(ctx, metered_lines=lines)

    from app.rules.variable_pricing import expected_amount

    assert expected_amount(terms, lines) == 3300.0
    result = check_r19(ctx, terms)
    assert result.result == "FALLA"
    assert result.on_fail == "FRENAR"
    assert decide(run_deterministic_checks(ctx)) == "FRENAR"


# --- §7 criterion 3: severity property test ---------------------------------------


def _optional_float(draw: st.DrawFn, *, min_value: float, max_value: float) -> float | None:
    floats = st.floats(min_value=min_value, max_value=max_value, allow_nan=False)
    return draw(st.one_of(st.none(), floats))


@st.composite
def _agreement_strategy(draw: st.DrawFn):
    kind = draw(st.sampled_from(("retainer", "hourly", "installments", "unit_pricing")))
    if kind == "retainer":
        lo = draw(st.floats(min_value=100, max_value=5000, allow_nan=False))
        return _retainer(
            amount={"min": lo, "max": lo},
            total_cap=_optional_float(draw, min_value=lo, max_value=lo * 20),
        )
    if kind == "hourly":
        rate = draw(st.floats(min_value=1, max_value=200, allow_nan=False))
        has_overtime = draw(st.booleans())
        overtime = (
            {"multiplier": draw(st.floats(min_value=1, max_value=3, allow_nan=False))}
            if has_overtime
            else None
        )
        return _hourly(
            rate=rate,
            included_hours=draw(st.floats(min_value=1, max_value=200, allow_nan=False)),
            overtime=overtime,
            period_cap=_optional_float(draw, min_value=100, max_value=20000),
        )
    if kind == "installments":
        amount = draw(st.floats(min_value=100, max_value=5000, allow_nan=False))
        item = {"key": "1/1", "due_from": "2026-02-01", "due_to": "2026-02-28", "amount": amount}
        return _installments(items=[item], total_cap=None)
    rate = draw(st.floats(min_value=1, max_value=200, allow_nan=False))
    return _unit_pricing(
        formula={"kind": "unit_rate", "unit": "hora", "rate": rate},
        period_cap=_optional_float(draw, min_value=100, max_value=20000),
    )


@seed(20261017)
@settings(max_examples=500, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    agreement=_agreement_strategy(),
    amount=st.floats(min_value=100, max_value=5000, allow_nan=False),
)
def test_compiled_rules_never_lower_severity_than_base(agreement, amount: float) -> None:
    """§7.3: with the vendor already allowed (T7.4 lane), compiled severity >= base severity."""
    base = load_rules_config(RULES_PATH)
    fx_table = load_fx_table(REPO_ROOT / "data" / "fx.json")
    vendor = agreement.vendor_name

    base_ctx = make_context(base, fx_table, beneficiary=vendor, amount=amount, amount_base=amount)
    base_decision = decide(run_deterministic_checks(base_ctx))

    compiled = compile_rules(base, [_active(agreement)])
    pricing = find_pricing_terms(compiled.rules, vendor)
    metered = ()
    if pricing is not None:
        formula = pricing.formula
        unit = getattr(formula, "unit", "hora")
        metered = (MeteredLine(quantity=10.0, unit=unit, source_span="10 unidades"),)
    compiled_ctx = make_context(
        compiled.rules,
        fx_table,
        beneficiary=vendor,
        amount=amount,
        amount_base=amount,
        doc_text="10 unidades",
    )
    compiled_ctx = replace(compiled_ctx, metered_lines=metered)
    compiled_decision = decide(run_deterministic_checks(compiled_ctx))

    assert SEVERITY[compiled_decision] >= SEVERITY[base_decision]


def test_new_vendor_without_human_approval_never_pays(
    base_rules: RulesConfig, fx_table: FxTable
) -> None:
    agreement = _retainer(vendor_name="Brand New Vendor LLC")
    compiled = compile_rules(base_rules, [_active(agreement)])
    assert "Brand New Vendor LLC" not in base_rules.allowed_beneficiaries

    ctx = make_context(
        compiled.rules,
        fx_table,
        beneficiary="Brand New Vendor LLC",
        amount=800,
        amount_base=800.0,
        due_date="2026-02-01",
    )
    checks = run_deterministic_checks(ctx)
    r20 = next(c for c in checks if c.rule == "R20")
    assert r20.result == "FALLA"
    assert decide(checks) != "PAGAR"


def test_new_vendor_after_human_approval_no_longer_fails_r20(
    base_rules: RulesConfig, fx_table: FxTable
) -> None:
    from app.rules.context import LedgerEntry

    agreement = _retainer(vendor_name="Brand New Vendor LLC")
    compiled = compile_rules(base_rules, [_active(agreement)])
    additions = compiled.rules.vendor_additions
    addition = next(a for a in additions if a.beneficiary == "Brand New Vendor LLC")

    ledger = (
        LedgerEntry(
            beneficiary="Brand New Vendor LLC",
            amount_base=800.0,
            currency="USD",
            invoice_number="INV-1",
            received_at="2026-02-02T00:00:00Z",
            decision="aprobada_humano",
        ),
    )
    ctx = make_context(
        compiled.rules,
        fx_table,
        beneficiary="Brand New Vendor LLC",
        amount=800,
        amount_base=800.0,
        due_date="2026-04-01",
        ledger=ledger,
    )
    checks = run_deterministic_checks(ctx)
    r20 = next(c for c in checks if c.rule == "R20")
    assert r20.result == "OK"
    assert addition.added_by == "cfo@demo.test"


# --- Product requirement (coordinator, 2026-10-18): variable-element agreements
# always floor at ESCALAR for human review, even when the recomputed amount
# matches exactly -- there is no ERP/CRM to verify the billed quantity itself.
# Overbilling still FRENAR (R19), unchanged.


def test_hourly_matching_amount_still_escalates_not_pagar(
    base_rules: RulesConfig, fx_table: FxTable
) -> None:
    agreement = _hourly(overtime=None, period_cap=None)  # unit_rate: 25/h, no overtime
    compiled = compile_rules(base_rules, [_active(agreement)])
    terms = next(p for p in compiled.rules.variable_pricing if p.beneficiary == "Andesbyte SAS")

    lines = (MeteredLine(quantity=20, unit="hora", source_span="20 horas"),)
    ctx = make_context(
        compiled.rules,
        fx_table,
        beneficiary="Andesbyte SAS",
        amount=500,  # exactly 20h * 25 = 500, matches
        amount_base=500.0,
        doc_text="20 horas",
    )
    ctx = replace(ctx, metered_lines=lines)

    result = check_r19(ctx, terms)
    assert result.result == "INDETERMINADO"
    decision = decide(run_deterministic_checks(ctx))
    assert decision != "PAGAR"
    assert SEVERITY[decision] >= SEVERITY["ESCALAR"]


def test_unit_pricing_matching_amount_still_escalates_not_pagar(
    base_rules: RulesConfig, fx_table: FxTable
) -> None:
    agreement = _unit_pricing(
        vendor_name="Pampaluz Ltda",
        formula={"kind": "unit_rate", "unit": "unidad", "rate": 10},
    )
    compiled = compile_rules(base_rules, [_active(agreement)])

    lines = (MeteredLine(quantity=50, unit="unidad", source_span="50 unidades"),)
    ctx = make_context(
        compiled.rules,
        fx_table,
        beneficiary="Pampaluz Ltda",
        amount=500,  # 50 * 10 = 500, matches exactly
        amount_base=500.0,
        doc_text="50 unidades",
    )
    ctx = replace(ctx, metered_lines=lines)

    decision = decide(run_deterministic_checks(ctx))
    assert decision != "PAGAR"


def test_hand_written_variable_pricing_unaffected_by_agreement_floor(
    f7_rules: RulesConfig, fx_table: FxTable
) -> None:
    """Regression: a hand-written `variable_pricing` entry (`contract_clause`
    like "4.2", never an `agr-` id) keeps its pre-T9.1 OK/PAGAR-eligible
    behavior -- only agreement-sourced entries get the new ESCALAR floor.
    """
    terms = next(p for p in f7_rules.variable_pricing if p.beneficiary == "Andesbyte SAS")
    assert not terms.contract_clause.startswith("agr-")

    lines = (MeteredLine(quantity=20, unit="hora", source_span="20 horas"),)
    ctx = make_context(
        f7_rules,
        fx_table,
        beneficiary="Andesbyte SAS",
        amount=1000,
        amount_base=1000.0,
        doc_text="20 horas",
    )
    ctx = replace(ctx, metered_lines=lines)

    assert check_r19(ctx, terms).result == "OK"
