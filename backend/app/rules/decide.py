"""T2.5 — Pure decision from check results (docs/04 §1). No LLM, no JEV, no verifier."""

from __future__ import annotations

from collections.abc import Sequence

from app.models.domain import SEVERITY, CheckResult, Decision


def _max_decision(left: Decision, right: Decision) -> Decision:
    return left if SEVERITY[left] >= SEVERITY[right] else right


def _severity_for_check(check: CheckResult) -> Decision:
    if check.result == "OK":
        return "PAGAR"
    if check.result == "INDETERMINADO":
        return "ESCALAR"
    if check.result == "FALLA":
        return check.on_fail if check.on_fail is not None else "ESCALAR"
    return "ESCALAR"


def decide(checks: Sequence[CheckResult]) -> Decision:
    """Aggregate rule outcomes: highest severity wins; indeterminate counts as ESCALAR."""
    if not checks:
        return "ESCALAR"
    outcome: Decision = "PAGAR"
    for check in checks:
        outcome = _max_decision(outcome, _severity_for_check(check))
    return outcome
