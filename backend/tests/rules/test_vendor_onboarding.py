"""T7.4 — Vendor onboarding (R20): first payment escalates until human approval."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.models.domain import SEVERITY
from app.models.rules_config import (
    VendorAddition,
    VendorOnboarding,
    load_rules_config,
)
from app.rules.checks import check_r20
from app.rules.context import LedgerEntry
from app.rules.decide import decide
from app.rules.fx import load_fx_table
from app.rules.run_checks import run_deterministic_checks
from hypothesis import HealthCheck, given, seed, settings
from hypothesis import strategies as st
from tests.rules.test_rules_r01_r13 import make_context

REPO_ROOT = Path(__file__).resolve().parents[3]


def _ledger_approval(
    beneficiary: str,
    received_at: str,
    *,
    invoice_number: str = "APR-1",
) -> LedgerEntry:
    return LedgerEntry(
        beneficiary=beneficiary,
        amount_base=0.0,
        currency="USD",
        invoice_number=invoice_number,
        received_at=received_at,
        decision="aprobada_humano",
    )


def test_r20_not_emitted_when_vendor_additions_empty() -> None:
    rules = load_rules_config(REPO_ROOT / "data" / "rules.json")
    fx = load_fx_table(REPO_ROOT / "data" / "fx.json")
    ctx = make_context(rules, fx, beneficiary="Globex LLC")
    results = run_deterministic_checks(ctx)
    assert all(r.rule != "R20" for r in results)


def test_r20_fails_until_human_approval_after_add() -> None:
    rules = load_rules_config(REPO_ROOT / "data" / "rules.json")
    added_at = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
    onboarded = rules.model_copy(
        update={
            "vendor_onboarding": VendorOnboarding(enabled=True),
            "vendor_additions": [
                VendorAddition(
                    beneficiary="Nuevo Vendor SAS",
                    added_at=added_at,
                    added_by="finanzas@demo.test",
                    reason="Primera factura",
                    source_decision_id="dec_r01",
                )
            ],
            "allowed_beneficiaries": [*rules.allowed_beneficiaries, "Nuevo Vendor SAS"],
        }
    )
    fx = load_fx_table(REPO_ROOT / "data" / "fx.json")
    ctx = make_context(
        onboarded,
        fx,
        beneficiary="Nuevo Vendor SAS",
        amount=500.0,
        amount_base=500.0,
    )
    fail = check_r20(ctx)
    assert fail.result == "FALLA"
    assert fail.on_fail == "ESCALAR"

    ctx_ok = make_context(
        onboarded,
        fx,
        beneficiary="Nuevo Vendor SAS",
        amount=500.0,
        amount_base=500.0,
        ledger=(
            _ledger_approval("Nuevo Vendor SAS", "2026-03-02T12:00:00Z"),
        ),
    )
    assert check_r20(ctx_ok).result == "OK"


def test_r20_ignores_pre_add_approvals() -> None:
    rules = load_rules_config(REPO_ROOT / "data" / "rules.json")
    added_at = datetime(2026, 3, 5, 10, 0, tzinfo=UTC)
    onboarded = rules.model_copy(
        update={
            "vendor_onboarding": VendorOnboarding(enabled=True),
            "vendor_additions": [
                VendorAddition(
                    beneficiary="Nuevo Vendor SAS",
                    added_at=added_at,
                    added_by="finanzas@demo.test",
                    reason="Alta",
                    source_decision_id="dec_x",
                )
            ],
            "allowed_beneficiaries": [*rules.allowed_beneficiaries, "Nuevo Vendor SAS"],
        }
    )
    fx = load_fx_table(REPO_ROOT / "data" / "fx.json")
    ctx = make_context(
        onboarded,
        fx,
        beneficiary="Nuevo Vendor SAS",
        ledger=(_ledger_approval("Nuevo Vendor SAS", "2026-03-01T12:00:00Z"),),
    )
    assert check_r20(ctx).result == "FALLA"


def test_re_eval_after_add_escalates_with_r20() -> None:
    rules = load_rules_config(REPO_ROOT / "data" / "rules.json")
    added_at = datetime(2026, 3, 4, 12, 0, tzinfo=UTC)
    onboarded = rules.model_copy(
        update={
            "vendor_onboarding": VendorOnboarding(enabled=True),
            "vendor_additions": [
                VendorAddition(
                    beneficiary="Nuevo Vendor SAS",
                    added_at=added_at,
                    added_by="cfo@demo.test",
                    reason="Alta auditada",
                    source_decision_id="dec_src",
                )
            ],
            "allowed_beneficiaries": [*rules.allowed_beneficiaries, "Nuevo Vendor SAS"],
        }
    )
    fx = load_fx_table(REPO_ROOT / "data" / "fx.json")
    ctx = make_context(
        onboarded,
        fx,
        beneficiary="Nuevo Vendor SAS",
        amount=800.0,
        amount_base=800.0,
    )
    decision = decide(run_deterministic_checks(ctx))
    assert decision == "ESCALAR"
    r20 = next(c for c in run_deterministic_checks(ctx) if c.rule == "R20")
    assert r20.result == "FALLA"


@seed(20261018)
@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    amount=st.floats(min_value=100, max_value=4000, allow_nan=False),
    beneficiary=st.sampled_from(["Globex LLC", "Initech SAS"]),
)
def test_vendor_additions_never_lowers_severity(amount: float, beneficiary: str) -> None:
    """R20 only applies once R01 already passes (beneficiary already allowed)."""
    rules = load_rules_config(REPO_ROOT / "data" / "rules.json")
    fx = load_fx_table(REPO_ROOT / "data" / "fx.json")
    base_ctx = make_context(rules, fx, beneficiary=beneficiary, amount=amount, amount_base=amount)
    base_decision = decide(run_deterministic_checks(base_ctx))

    added_at = datetime(2026, 2, 1, 8, 0, tzinfo=UTC)
    addition = VendorAddition(
        beneficiary=beneficiary,
        added_at=added_at,
        added_by="finanzas@demo.test",
        reason="prop",
        source_decision_id="dec_prop",
    )
    onboarded = rules.model_copy(
        update={
            "vendor_onboarding": VendorOnboarding(enabled=True),
            "vendor_additions": [addition],
        }
    )
    onboard_ctx = make_context(
        onboarded,
        fx,
        beneficiary=beneficiary,
        amount=amount,
        amount_base=amount,
    )
    onboard_decision = decide(run_deterministic_checks(onboard_ctx))
    assert SEVERITY[onboard_decision] >= SEVERITY[base_decision]
