"""T7.3 — Variable pricing (R19): recomputation, extraction, severity property."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from app.models.metered import MeteredLine
from app.models.rules_config import (
    CommissionFormula,
    PricingTerms,
    RulesConfig,
    TieredFormula,
    TieredTier,
    UnitRateFormula,
    load_rules_config,
)
from app.rules.checks import check_r19
from app.rules.context import RuleContext
from app.rules.decide import decide
from app.rules.fx import FxTable, load_fx_table
from app.rules.run_checks import run_deterministic_checks
from app.rules.variable_pricing import expected_amount
from hypothesis import HealthCheck, given, seed, settings
from hypothesis import strategies as st
from tests.rules.test_rules_r01_r13 import make_context as _base_context

REPO_ROOT = Path(__file__).resolve().parents[3]
F7_RULES = REPO_ROOT / "data" / "f7" / "rules.json"


@pytest.fixture(scope="module")
def rules() -> RulesConfig:
    return load_rules_config(REPO_ROOT / "data" / "rules.json")


@pytest.fixture(scope="module")
def fx_table() -> FxTable:
    return load_fx_table(REPO_ROOT / "data" / "fx.json")


@pytest.fixture(scope="module")
def f7_rules() -> RulesConfig:
    return load_rules_config(F7_RULES)


def _ctx(
    rules: RulesConfig,
    fx_table: FxTable,
    *,
    metered_lines: tuple[MeteredLine, ...] = (),
    doc_text: str = "",
    **kwargs: object,
) -> RuleContext:
    base = _base_context(rules, fx_table, doc_text=doc_text, **kwargs)  # type: ignore[arg-type]
    return replace(base, metered_lines=metered_lines)


def _andesbyte_terms(f7_rules: RulesConfig) -> PricingTerms:
    return next(t for t in f7_rules.variable_pricing if t.beneficiary == "Andesbyte SAS")


def _line(**kwargs: object) -> MeteredLine:
    return MeteredLine.model_validate(kwargs)


def test_unit_rate_expected_amount() -> None:
    terms = PricingTerms(
        beneficiary="X",
        currency="USD",
        contract_clause="4.2",
        formula=UnitRateFormula(kind="unit_rate", unit="hora", rate=50),
    )
    lines = (_line(quantity=20, unit="hora", source_span="20 horas"),)
    assert expected_amount(terms, lines) == 1000.0


def test_unit_rate_cap_limits_total() -> None:
    terms = PricingTerms(
        beneficiary="X",
        currency="USD",
        contract_clause="4.2",
        formula=UnitRateFormula(kind="unit_rate", unit="hora", rate=50, cap=600),
    )
    lines = (_line(quantity=20, unit="hora", source_span="20"),)
    assert expected_amount(terms, lines) == 600.0


def test_tiered_edge_of_first_band() -> None:
    terms = PricingTerms(
        beneficiary="X",
        currency="USD",
        contract_clause="4.3",
        formula=TieredFormula(
            kind="tiered",
            unit="unidad",
            tiers=[TieredTier(up_to=100, rate=10), TieredTier(up_to=None, rate=8)],
        ),
    )
    lines = (_line(quantity=100, unit="unidad", source_span="100 unidades"),)
    assert expected_amount(terms, lines) == 1000.0


def test_tiered_spans_second_band() -> None:
    terms = PricingTerms(
        beneficiary="X",
        currency="USD",
        contract_clause="4.3",
        formula=TieredFormula(
            kind="tiered",
            unit="unidad",
            tiers=[TieredTier(up_to=100, rate=10), TieredTier(up_to=None, rate=8)],
        ),
    )
    lines = (_line(quantity=101, unit="unidad", source_span="101"),)
    assert expected_amount(terms, lines) == 1008.0


def test_commission_on_base() -> None:
    terms = PricingTerms(
        beneficiary="X",
        currency="COP",
        contract_clause="4.4",
        formula=CommissionFormula(kind="commission", pct=5, base_label="ventas"),
    )
    lines = (_line(unit="ventas", base_amount=20_000_000, source_span="COP 20.000.000"),)
    assert expected_amount(terms, lines) == 1_000_000.0


def test_tolerance_allows_small_overbill(f7_rules: RulesConfig, fx_table: FxTable) -> None:
    terms = _andesbyte_terms(f7_rules)
    lines = (_line(quantity=20, unit="hora", unit_rate=50, source_span="20 horas"),)
    ctx = _ctx(
        f7_rules,
        fx_table,
        beneficiary="Andesbyte SAS",
        amount=1000.5,
        currency="USD",
        amount_base=1000.5,
        fee_amount=500,
        fee_currency="EUR",
        metered_lines=lines,
    )
    assert check_r19(ctx, terms).result == "OK"


def test_wrong_unit_is_indeterminate(f7_rules: RulesConfig, fx_table: FxTable) -> None:
    terms = _andesbyte_terms(f7_rules)
    lines = (_line(quantity=20, unit="dia", source_span="20 dias"),)
    ctx = _ctx(
        f7_rules,
        fx_table,
        beneficiary="Andesbyte SAS",
        amount=1000,
        currency="USD",
        amount_base=1000.0,
        metered_lines=lines,
    )
    assert check_r19(ctx, terms).result == "INDETERMINADO"


def test_missing_quote_in_doc_is_indeterminate(f7_rules: RulesConfig, fx_table: FxTable) -> None:
    terms = _andesbyte_terms(f7_rules)
    lines = (_line(quantity=20, unit="hora", source_span="no-esta-en-el-doc"),)
    ctx = _ctx(
        f7_rules,
        fx_table,
        beneficiary="Andesbyte SAS",
        amount=1000,
        currency="USD",
        amount_base=1000.0,
        doc_text="Factura por 20 horas de trabajo.",
        metered_lines=lines,
    )
    assert check_r19(ctx, terms).result == "INDETERMINADO"


def test_overbill_frenar(f7_rules: RulesConfig, fx_table: FxTable) -> None:
    terms = _andesbyte_terms(f7_rules)
    lines = (_line(quantity=20, unit="hora", source_span="20 horas"),)
    ctx = _ctx(
        f7_rules,
        fx_table,
        beneficiary="Andesbyte SAS",
        amount=1300,
        currency="USD",
        amount_base=1300.0,
        fee_amount=500,
        fee_currency="EUR",
        metered_lines=lines,
    )
    result = check_r19(ctx, terms)
    assert result.result == "FALLA"
    assert result.on_fail == "FRENAR"


def test_without_variable_pricing_config_r19_not_emitted(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    results = run_deterministic_checks(_ctx(rules, fx_table))
    assert all(r.rule != "R19" for r in results)


def test_r19_never_enables_pagar_when_r06_escalates(
    f7_rules: RulesConfig, fx_table: FxTable
) -> None:
    terms = _andesbyte_terms(f7_rules)
    lines = (_line(quantity=20, unit="hora", source_span="20 horas"),)
    ctx = _ctx(
        f7_rules,
        fx_table,
        beneficiary="Andesbyte SAS",
        amount=1000,
        currency="USD",
        amount_base=1000.0,
        fee_amount=500,
        fee_currency="EUR",
        metered_lines=lines,
    )
    checks = run_deterministic_checks(ctx)
    assert check_r19(ctx, terms).result == "OK"
    assert decide(checks) == "ESCALAR"


@st.composite
def _pricing_terms_payload(draw: st.DrawFn) -> dict:
    kind = draw(st.sampled_from(("unit_rate", "tiered", "commission")))
    if kind == "unit_rate":
        formula = {
            "kind": "unit_rate",
            "unit": draw(st.sampled_from(("hora", "unidad"))),
            "rate": draw(st.floats(min_value=1, max_value=500, allow_nan=False)),
        }
        if draw(st.booleans()):
            formula["cap"] = draw(st.floats(min_value=1, max_value=5000, allow_nan=False))
    elif kind == "tiered":
        formula = {
            "kind": "tiered",
            "unit": "unidad",
            "tiers": [
                {"up_to": 100, "rate": 10},
                {"up_to": None, "rate": 8},
            ],
        }
    else:
        formula = {"kind": "commission", "pct": 5, "base_label": "ventas"}
    tol = draw(st.one_of(st.none(), st.just({"abs": 1.0})))
    payload = {
        "beneficiary": "Globex LLC",
        "currency": "USD",
        "contract_clause": "4.2",
        "formula": formula,
    }
    if tol is not None:
        payload["tolerance"] = tol
    return payload


@seed(20261017)
@settings(max_examples=500, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    pricing_payload=_pricing_terms_payload(),
    amount=st.floats(min_value=100, max_value=5000, allow_nan=False),
    quantity=st.floats(min_value=1, max_value=200, allow_nan=False),
)
def test_adding_variable_pricing_never_lowers_severity(
    pricing_payload: dict,
    amount: float,
    quantity: float,
) -> None:
    rules = load_rules_config(REPO_ROOT / "data" / "rules.json")
    fx_table = load_fx_table(REPO_ROOT / "data" / "fx.json")
    base_ctx = _ctx(rules, fx_table, beneficiary="Globex LLC", amount=amount, amount_base=amount)
    base_decision = decide(run_deterministic_checks(base_ctx))

    terms = PricingTerms.model_validate(pricing_payload)
    priced_rules = rules.model_copy(update={"variable_pricing": [terms]})
    formula = pricing_payload["formula"]
    unit = formula["unit"] if formula["kind"] != "commission" else "ventas"
    metered = (
        _line(
            quantity=quantity if pricing_payload["formula"]["kind"] != "commission" else None,
            unit=unit,
            base_amount=amount * 4 if pricing_payload["formula"]["kind"] == "commission" else None,
            source_span="literal-cita-en-doc",
        ),
    )
    priced_ctx = _ctx(
        priced_rules,
        fx_table,
        beneficiary="Globex LLC",
        amount=amount,
        amount_base=amount,
        doc_text="literal-cita-en-doc",
        metered_lines=metered,
    )
    priced_decision = decide(run_deterministic_checks(priced_ctx))

    from app.models.domain import SEVERITY

    assert SEVERITY[priced_decision] >= SEVERITY[base_decision]
