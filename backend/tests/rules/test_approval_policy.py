"""T7.1 — R14 approval-policy routes: schema, resolve_route, composition with decide().

Acceptance criteria 1, 3 and 4 of docs/T7_1_SPEC.md (AI-TDD). R14 can only ADD
approval requirements; it must never turn a non-PAGAR decision into PAGAR (I1).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from app.models.domain import SEVERITY
from app.models.rules_config import ApprovalPolicy, RulesConfig, load_rules_config
from app.rules.approval_policy import (
    ApprovalPolicyGroupError,
    parse_r14_quote,
    resolve_route,
    validate_policy_groups,
)
from app.rules.checks import CHECKS, check_r14
from app.rules.decide import decide
from app.rules.fx import FxTable, load_fx_table
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


def _policy(*routes: dict) -> ApprovalPolicy:
    return ApprovalPolicy.model_validate({"routes": list(routes)})


MARKETING_CFO = {
    "id": "marketing-cfo",
    "match": {"department": "Marketing"},
    "require": {"mode": "approvals", "min_approvals": 1, "from_groups": ["cfo"]},
}
ALTO_MONTO = {
    "id": "alto-monto",
    "match": {"amount_base_gte": 3000},
    "require": {"mode": "approvals", "min_approvals": 2, "from_groups": ["finanzas", "cfo"]},
}
DEFAULT_AUTO = {"id": "default", "match": {}, "require": {"mode": "auto"}}


# --- schema: routes, catch-all, unique ids (criterion 1) ----------------------------


def test_default_rules_json_has_no_approval_policy(rules: RulesConfig) -> None:
    assert rules.approval_policy is None


def test_approval_policy_requires_catch_all_last() -> None:
    with pytest.raises(ValidationError):
        _policy(MARKETING_CFO, ALTO_MONTO)  # no catch-all


def test_approval_policy_rejects_duplicate_ids() -> None:
    with pytest.raises(ValidationError):
        _policy(ALTO_MONTO, {**ALTO_MONTO, "match": {}}, DEFAULT_AUTO)


def test_approval_policy_rejects_non_empty_catch_all_match() -> None:
    with pytest.raises(ValidationError):
        _policy({"id": "default", "match": {"department": "X"}, "require": {"mode": "auto"}})


def test_approvals_mode_requires_min_approvals_and_groups() -> None:
    with pytest.raises(ValidationError):
        _policy({"id": "default", "match": {}, "require": {"mode": "approvals"}})


def test_auto_mode_forbids_min_approvals_and_groups() -> None:
    with pytest.raises(ValidationError):
        _policy(
            {
                "id": "default",
                "match": {},
                "require": {"mode": "auto", "min_approvals": 1, "from_groups": ["cfo"]},
            }
        )


def test_approval_policy_accepts_the_spec_example() -> None:
    policy = _policy(MARKETING_CFO, ALTO_MONTO, DEFAULT_AUTO)
    assert [r.id for r in policy.routes] == ["marketing-cfo", "alto-monto", "default"]


# --- resolve_route: first match wins, missing data -> indeterminate ----------------


def test_resolve_route_first_match_wins(rules: RulesConfig, fx_table: FxTable) -> None:
    policy = _policy(MARKETING_CFO, ALTO_MONTO, DEFAULT_AUTO)
    ctx = make_context(rules, fx_table, amount_base=4200.0, department="Marketing")
    resolution = resolve_route(policy, ctx.extraction, 4200.0)
    assert resolution.route is not None
    assert resolution.route.id == "marketing-cfo"


def test_resolve_route_second_route_when_first_does_not_match(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    policy = _policy(MARKETING_CFO, ALTO_MONTO, DEFAULT_AUTO)
    ctx = make_context(rules, fx_table, amount_base=4200.0, department="Ingenieria")
    resolution = resolve_route(policy, ctx.extraction, 4200.0)
    assert resolution.route is not None
    assert resolution.route.id == "alto-monto"


def test_resolve_route_catch_all_when_nothing_matches(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    policy = _policy(MARKETING_CFO, ALTO_MONTO, DEFAULT_AUTO)
    ctx = make_context(rules, fx_table, amount_base=360.0, department="Ingenieria")
    resolution = resolve_route(policy, ctx.extraction, 360.0)
    assert resolution.route is not None
    assert resolution.route.id == "default"
    assert resolution.route.require.mode == "auto"


def test_resolve_route_missing_amount_is_indeterminate(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    policy = _policy(ALTO_MONTO, DEFAULT_AUTO)
    ctx = make_context(rules, fx_table, amount_base=None, amount=None)
    resolution = resolve_route(policy, ctx.extraction, None)
    assert resolution.route is None
    assert resolution.reason is not None


def test_resolve_route_missing_department_is_indeterminate(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    policy = _policy(MARKETING_CFO, DEFAULT_AUTO)
    ctx = make_context(rules, fx_table, department=None)
    resolution = resolve_route(policy, ctx.extraction, 800.0)
    assert resolution.route is None


# --- check_r14: composes with decide(), never downgrades severity ------------------


def test_check_r14_ok_on_auto_route(rules: RulesConfig, fx_table: FxTable) -> None:
    policy = _policy(DEFAULT_AUTO)
    policy_rules = rules.model_copy(update={"approval_policy": policy})
    ctx = make_context(policy_rules, fx_table, amount_base=360.0)
    result = check_r14(ctx)
    assert result.result == "OK"


def test_check_r14_falla_with_route_and_groups_in_evidence(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    policy = _policy(ALTO_MONTO, DEFAULT_AUTO)
    policy_rules = rules.model_copy(update={"approval_policy": policy})
    ctx = make_context(policy_rules, fx_table, amount_base=4200.0)
    result = check_r14(ctx)
    assert result.result == "FALLA"
    assert result.on_fail == "ESCALAR"
    assert result.evidence is not None
    assert result.evidence.clause == "alto-monto"
    assert result.evidence.quote == "min_approvals=2;groups=cfo,finanzas"
    assert parse_r14_quote(result.evidence.quote) == (2, ["cfo", "finanzas"])


def test_check_r14_indeterminate_missing_department(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    policy = _policy(MARKETING_CFO, DEFAULT_AUTO)
    policy_rules = rules.model_copy(update={"approval_policy": policy})
    ctx = make_context(policy_rules, fx_table, department=None)
    result = check_r14(ctx)
    assert result.result == "INDETERMINADO"


def test_run_deterministic_checks_without_policy_is_byte_identical_to_13_checks(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    """Criterion 2: no approval_policy -> R14 is never emitted."""
    assert rules.approval_policy is None
    ctx = make_context(rules, fx_table)
    results = run_deterministic_checks(ctx)
    assert len(results) == len(CHECKS) == 13
    assert all(r.rule != "R14" for r in results)


def test_run_deterministic_checks_with_policy_appends_r14_only(
    rules: RulesConfig, fx_table: FxTable
) -> None:
    policy = _policy(ALTO_MONTO, DEFAULT_AUTO)
    policy_rules = rules.model_copy(update={"approval_policy": policy})
    ctx_base = make_context(rules, fx_table, amount_base=4200.0)
    ctx_policy = replace(ctx_base, rules=policy_rules)

    base_checks = run_deterministic_checks(ctx_base)
    policy_checks = run_deterministic_checks(ctx_policy)

    assert len(policy_checks) == len(base_checks) + 1
    assert [c.rule for c in policy_checks[:-1]] == [c.rule for c in base_checks]
    assert policy_checks[-1].rule == "R14"


def test_r14_never_turns_escalar_into_pagar(rules: RulesConfig, fx_table: FxTable) -> None:
    """Concrete case: amount under threshold, but a route still demands approval."""
    policy = _policy(MARKETING_CFO, DEFAULT_AUTO)
    policy_rules = rules.model_copy(update={"approval_policy": policy})
    ctx_base = make_context(
        rules, fx_table, amount_base=600.0, department="Marketing", fee_amount=600.0
    )
    ctx_policy = replace(ctx_base, rules=policy_rules)

    assert decide(run_deterministic_checks(ctx_base)) == "PAGAR"
    assert decide(run_deterministic_checks(ctx_policy)) == "ESCALAR"


# --- company.json cross-check: group existence + reachable min_approvals -----------


def test_validate_policy_groups_rejects_unknown_group() -> None:
    policy = _policy(MARKETING_CFO, DEFAULT_AUTO)
    with pytest.raises(ApprovalPolicyGroupError):
        validate_policy_groups(policy, {"finanzas": frozenset({"a@demo.test"})})


def test_validate_policy_groups_rejects_unreachable_min_approvals() -> None:
    policy = _policy(ALTO_MONTO, DEFAULT_AUTO)
    with pytest.raises(ApprovalPolicyGroupError):
        validate_policy_groups(
            policy,
            {
                "finanzas": frozenset({"finanzas@demo.test"}),
                "cfo": frozenset({"finanzas@demo.test"}),  # same single person, union size 1 < 2
            },
        )


def test_validate_policy_groups_accepts_reachable_policy() -> None:
    policy = _policy(ALTO_MONTO, MARKETING_CFO, DEFAULT_AUTO)
    validate_policy_groups(
        policy,
        {
            "finanzas": frozenset({"finanzas@demo.test"}),
            "cfo": frozenset({"cfo@demo.test"}),
        },
    )


def test_validate_policy_groups_none_policy_is_noop() -> None:
    validate_policy_groups(None, {})


def test_parse_r14_quote_rejects_malformed_text() -> None:
    assert parse_r14_quote(None) is None
    assert parse_r14_quote("not-a-quote") is None
    assert parse_r14_quote("min_approvals=0;groups=cfo") is None
    assert parse_r14_quote("min_approvals=1;groups=") is None


# --- property test (criterion 3): severity never decreases with a policy -----------

_GROUPS = ("finanzas", "cfo", "legal")
_DEPARTMENTS = ("Ingenieria", "Marketing", "Otro")
_INVOICE_TYPES = ("servicios", "productos", "suscripción", "honorarios", "otro")


@st.composite
def _route_match(draw: st.DrawFn) -> dict:
    match: dict = {}
    if draw(st.booleans()):
        match["amount_base_gte"] = draw(st.floats(min_value=0, max_value=10_000, allow_nan=False))
    if draw(st.booleans()):
        match["department"] = draw(st.sampled_from(_DEPARTMENTS))
    if draw(st.booleans()):
        match["invoice_type"] = draw(st.sampled_from(_INVOICE_TYPES))
    if draw(st.booleans()):
        match["beneficiary"] = draw(st.sampled_from(["Globex LLC", "Initech SAS"]))
    return match


@st.composite
def _route_require(draw: st.DrawFn) -> dict:
    if draw(st.booleans()):
        return {"mode": "auto"}
    groups = draw(st.lists(st.sampled_from(_GROUPS), min_size=1, max_size=3, unique=True))
    min_approvals = draw(st.integers(min_value=1, max_value=5))
    return {"mode": "approvals", "min_approvals": min_approvals, "from_groups": groups}


@st.composite
def _policy_payload(draw: st.DrawFn) -> dict:
    n = draw(st.integers(min_value=0, max_value=3))
    routes = [
        {"id": f"r{i}", "match": draw(_route_match()), "require": draw(_route_require())}
        for i in range(n)
    ]
    routes.append({"id": "default", "match": {}, "require": draw(_route_require())})
    return {"routes": routes}


@seed(20261017)
@settings(max_examples=500, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    policy_payload=_policy_payload(),
    amount_base=st.one_of(st.none(), st.floats(min_value=0, max_value=20_000, allow_nan=False)),
    department=st.one_of(st.none(), st.sampled_from(_DEPARTMENTS)),
    invoice_type=st.one_of(st.none(), st.sampled_from(_INVOICE_TYPES)),
    beneficiary=st.one_of(st.none(), st.sampled_from(["Globex LLC", "Initech SAS"])),
)
def test_applying_any_approval_policy_never_lowers_severity(
    policy_payload: dict,
    amount_base: float | None,
    department: str | None,
    invoice_type: str | None,
    beneficiary: str | None,
) -> None:
    rules = load_rules_config(REPO_ROOT / "data" / "rules.json")
    fx_table = load_fx_table(REPO_ROOT / "data" / "fx.json")
    policy = ApprovalPolicy.model_validate(policy_payload)
    policy_rules = rules.model_copy(update={"approval_policy": policy})

    ctx_base = make_context(
        rules,
        fx_table,
        amount_base=amount_base,
        amount=amount_base,
        department=department,
    )
    extraction_update: dict[str, object] = {"invoice_type": invoice_type}
    if beneficiary is not None:
        extraction_update["beneficiary"] = beneficiary
    ctx_base = replace(
        ctx_base, extraction=ctx_base.extraction.model_copy(update=extraction_update)
    )
    ctx_policy = replace(ctx_base, rules=policy_rules)

    decision_base = decide(run_deterministic_checks(ctx_base))
    decision_policy = decide(run_deterministic_checks(ctx_policy))

    assert SEVERITY[decision_policy] >= SEVERITY[decision_base]
    if decision_base != "PAGAR":
        assert decision_policy != "PAGAR"
