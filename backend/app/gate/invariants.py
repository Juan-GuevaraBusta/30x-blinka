"""Pure invariant predicates for final_gate (docs/04 §7, AGENTS.md I1–I4)."""

from __future__ import annotations

from app.models.domain import (
    SEVERITY,
    CheckResult,
    Decision,
    JevSignal,
    VerifierReport,
)
from app.models.rules_config import JevThresholds

_REQUIRED_JEV_FOR_PAGAR: tuple[str, ...] = ("J1", "J2", "J3", "J4")
_OPTIONAL_JEV_FOR_PAGAR: tuple[str, ...] = ("J6", "J7")


def severity_of(decision: Decision) -> int:
    return SEVERITY[decision]


def max_decision(d1: Decision, d2: Decision) -> Decision:
    return d1 if severity_of(d1) >= severity_of(d2) else d2


def checks_allow_pagar(checks: list[CheckResult]) -> bool:
    if not checks:
        return False
    return all(check.result == "OK" for check in checks)


def _jev_threshold(thresholds: JevThresholds, jev_id: str) -> float:
    return getattr(thresholds, jev_id)


def jev_allows_pagar(signals: list[JevSignal], thresholds: JevThresholds) -> bool:
    by_id = {signal.id: signal for signal in signals}
    for jev_id in _REQUIRED_JEV_FOR_PAGAR:
        signal = by_id.get(jev_id)
        if signal is None or signal.answer is not True:
            return False
        if signal.probability < _jev_threshold(thresholds, jev_id):
            return False
    for jev_id in _OPTIONAL_JEV_FOR_PAGAR:
        signal = by_id.get(jev_id)
        if signal is None:
            continue
        if signal.answer is not True:
            return False
        if signal.probability < _jev_threshold(thresholds, jev_id):
            return False
    return True


def apply_verifier_severity_floor(proposed: Decision, report: VerifierReport) -> Decision:
    if any(issue.kind == "violation" for issue in report.issues):
        floor: Decision = "FRENAR"
    elif not report.consistent or any(issue.kind == "uncertainty" for issue in report.issues):
        floor = "ESCALAR"
    else:
        floor = "PAGAR"
    return max_decision(proposed, floor)


def explanation_covers_failed_checks(summary: str, checks: list[CheckResult]) -> bool:
    for check in checks:
        if check.result == "OK":
            continue
        if check.rule not in summary:
            return False
    return True
