"""Deterministic invariant gate (QA). No rules engine or LLM."""

from app.gate.final_gate import GateInput, GateOutput, run_final_gate
from app.gate.invariants import (
    apply_verifier_severity_floor,
    checks_allow_pagar,
    explanation_covers_failed_checks,
    jev_allows_pagar,
    max_decision,
    severity_of,
)

__all__ = [
    "GateInput",
    "GateOutput",
    "apply_verifier_severity_floor",
    "checks_allow_pagar",
    "explanation_covers_failed_checks",
    "jev_allows_pagar",
    "max_decision",
    "run_final_gate",
    "severity_of",
]
