"""Deterministic final gate after decide() and verifier (docs/04 §7)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.gate.invariants import (
    apply_verifier_severity_floor,
    checks_allow_pagar,
    explanation_covers_failed_checks,
    jev_allows_pagar,
    max_decision,
    severity_of,
)
from app.models.domain import SEVERITY, Decision, DecisionRecord
from app.models.rules_config import JevThresholds

_INVARIANT_SUMMARY = (
    "Escalada: no fue posible verificar la factura de forma confiable "
    "(invariante_violado). Requiere revisión humana."
)
_INVARIANT_NEXT_STEP = "Revisión por violación de invariante: invariante_violado."


class GateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposed_decision: Decision
    record: DecisionRecord
    jev_thresholds: JevThresholds


class GateOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    final_decision: Decision
    record: DecisionRecord
    gate_violations: list[str]


def _collect_violations(
    candidate: Decision,
    proposed: Decision,
    record: DecisionRecord,
    thresholds: JevThresholds,
) -> list[str]:
    violations: list[str] = []
    if candidate == "PAGAR":
        if not checks_allow_pagar(record.checks):
            violations.append("I1_checks")
        if not jev_allows_pagar(record.jev_signals, thresholds):
            violations.append("I1_jev")
    if (
        not record.verifier.consistent
        and (candidate == "PAGAR" or (proposed == "PAGAR" and candidate != "FRENAR"))
    ):
        violations.append("I1_verifier")
    if candidate == "FRENAR":
        notice = record.admin_notice
        if notice is None or not notice.strip():
            violations.append("I5_pending")
    if not explanation_covers_failed_checks(record.summary, record.checks):
        violations.append("explanation_gap")
    return violations


def _apply_final_to_record(record: DecisionRecord, final: Decision) -> DecisionRecord:
    if record.decision == final and record.severity == SEVERITY[final]:
        return record
    return record.model_copy(
        update={"decision": final, "severity": severity_of(final)},
    )


def run_final_gate(inp: GateInput) -> GateOutput:
    proposed = inp.proposed_decision
    record = inp.record
    candidate = apply_verifier_severity_floor(proposed, record.verifier)
    candidate = max_decision(candidate, proposed)

    violations = _collect_violations(candidate, proposed, record, inp.jev_thresholds)

    if violations:
        final: Decision = "ESCALAR"
        updated = record.model_copy(
            update={
                "decision": final,
                "severity": SEVERITY[final],
                "summary": _INVARIANT_SUMMARY,
                "next_step": _INVARIANT_NEXT_STEP,
            },
        )
        return GateOutput(
            final_decision=final,
            record=updated,
            gate_violations=violations,
        )

    final = candidate
    if final == "PAGAR" and (
        not checks_allow_pagar(record.checks)
        or not jev_allows_pagar(record.jev_signals, inp.jev_thresholds)
        or not record.verifier.consistent
    ):
        final = "ESCALAR"
        violations = ["I1_checks"]
        updated = record.model_copy(
            update={
                "decision": final,
                "severity": SEVERITY[final],
                "summary": _INVARIANT_SUMMARY,
                "next_step": _INVARIANT_NEXT_STEP,
            },
        )
        return GateOutput(
            final_decision=final,
            record=updated,
            gate_violations=violations,
        )

    updated = _apply_final_to_record(record, final)
    return GateOutput(final_decision=final, record=updated, gate_violations=[])
