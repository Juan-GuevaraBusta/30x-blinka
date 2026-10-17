"""T2.7 — invariant predicates and property tests I1 / I4."""

from __future__ import annotations

from app.gate.invariants import (
    apply_verifier_severity_floor,
    checks_allow_pagar,
    jev_allows_pagar,
    max_decision,
)
from app.models.domain import SEVERITY, VerifierIssue
from conftest import RULE_CODES, default_thresholds, make_check, make_jev, make_verifier
from hypothesis import given
from hypothesis import strategies as st


def test_checks_allow_pagar_all_ok() -> None:
    checks = [make_check("R01", "OK"), make_check("R02", "OK")]
    assert checks_allow_pagar(checks) is True


def test_checks_allow_pagar_false_on_falla() -> None:
    checks = [make_check("R01", "OK"), make_check("R02", "FALLA", on_fail="ESCALAR")]
    assert checks_allow_pagar(checks) is False


def test_checks_allow_pagar_false_on_indeterminado() -> None:
    checks = [make_check("R06", "INDETERMINADO")]
    assert checks_allow_pagar(checks) is False


def test_checks_allow_pagar_false_on_empty() -> None:
    assert checks_allow_pagar([]) is False


def test_max_decision_pagar_escalar_frenar_order() -> None:
    assert max_decision("PAGAR", "ESCALAR") == "ESCALAR"
    assert max_decision("ESCALAR", "FRENAR") == "FRENAR"
    assert max_decision("PAGAR", "FRENAR") == "FRENAR"
    assert max_decision("FRENAR", "ESCALAR") == "FRENAR"


def test_jev_allows_pagar_requires_j1_j4_above_threshold() -> None:
    thresholds = default_thresholds()
    assert jev_allows_pagar(make_jev(), thresholds) is True


def test_jev_rejects_missing_j3() -> None:
    thresholds = default_thresholds()
    signals = [s for s in make_jev() if s.id != "J3"]
    assert jev_allows_pagar(signals, thresholds) is False


def test_jev_rejects_low_probability() -> None:
    thresholds = default_thresholds()
    signals = make_jev(j1=0.5)
    assert jev_allows_pagar(signals, thresholds) is False


def test_apply_verifier_floor_violation_to_frenar() -> None:
    report = make_verifier(
        consistent=False,
        issues=(
            VerifierIssue(
                code="V1",
                kind="violation",
                evidence="campo contradictorio",
            ),
        ),
    )
    assert apply_verifier_severity_floor("PAGAR", report) == "FRENAR"


def test_apply_verifier_floor_uncertainty_to_escalar() -> None:
    report = make_verifier(
        consistent=True,
        issues=(
            VerifierIssue(code="U1", kind="uncertainty", evidence="duda"),
        ),
    )
    assert apply_verifier_severity_floor("PAGAR", report) == "ESCALAR"


def test_apply_verifier_floor_does_not_lower_frenar() -> None:
    report = make_verifier(consistent=True, issues=())
    assert apply_verifier_severity_floor("FRENAR", report) == "FRENAR"


@given(
    statuses=st.lists(
        st.sampled_from(["OK", "FALLA", "INDETERMINADO"]),
        min_size=1,
        max_size=13,
    ),
)
def test_i1_no_pagar_when_any_non_ok(statuses: list[str]) -> None:
    checks = [
        make_check(RULE_CODES[i % len(RULE_CODES)], status) for i, status in enumerate(statuses)
    ]
    if any(status != "OK" for status in statuses):
        assert checks_allow_pagar(checks) is False


@given(
    d1=st.sampled_from(["PAGAR", "ESCALAR", "FRENAR"]),
    d2=st.sampled_from(["PAGAR", "ESCALAR", "FRENAR"]),
)
def test_i4_max_decision_never_below_inputs(d1: str, d2: str) -> None:
    merged = max_decision(d1, d2)
    assert SEVERITY[merged] >= SEVERITY[d1]
    assert SEVERITY[merged] >= SEVERITY[d2]
