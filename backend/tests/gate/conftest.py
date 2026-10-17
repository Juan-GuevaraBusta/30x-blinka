"""Synthetic builders for gate tests (docs/04 §5 shapes)."""

from __future__ import annotations

from datetime import date

from app.models.domain import (
    SEVERITY,
    CheckResult,
    CheckStatus,
    Decision,
    DecisionRecord,
    FailAction,
    JevSignal,
    RuleCode,
    VerifierIssue,
    VerifierReport,
)
from app.models.rules_config import JevThresholds

RULE_CODES: tuple[RuleCode, ...] = (
    "R01",
    "R02",
    "R03",
    "R04",
    "R05",
    "R06",
    "R07",
    "R08",
    "R09",
    "R10",
    "R11",
    "R12",
    "R13",
)


def default_thresholds() -> JevThresholds:
    return JevThresholds(J1=0.9, J2=0.9, J3=0.85, J4=0.85, J6=0.85, J7=0.5)


def make_check(
    rule: RuleCode,
    result: CheckStatus,
    *,
    on_fail: FailAction | None = None,
    detail: str = "detalle sintético de prueba.",
    name: str = "Chequeo sintético",
) -> CheckResult:
    payload: dict = {
        "rule": rule,
        "name": name,
        "result": result,
        "detail": detail,
    }
    if on_fail is not None:
        payload["on_fail"] = on_fail
    return CheckResult.model_validate(payload)


def make_jev(
    *,
    j1: float = 0.95,
    j2: float = 0.95,
    j3: float = 0.9,
    j4: float = 0.9,
    include_j6_j7: bool = False,
) -> list[JevSignal]:
    signals = [
        JevSignal(id="J1", answer=True, probability=j1),
        JevSignal(id="J2", answer=True, probability=j2),
        JevSignal(id="J3", answer=True, probability=j3),
        JevSignal(id="J4", answer=True, probability=j4),
    ]
    if include_j6_j7:
        signals.extend(
            [
                JevSignal(id="J6", answer=True, probability=0.9),
                JevSignal(id="J7", answer=True, probability=0.6),
            ]
        )
    return signals


def make_verifier(
    *,
    consistent: bool = True,
    issues: tuple[VerifierIssue, ...] = (),
) -> VerifierReport:
    return VerifierReport(consistent=consistent, issues=list(issues))


def all_ok_checks() -> list[CheckResult]:
    return [make_check(rule, "OK", name=f"Regla {rule}") for rule in RULE_CODES]


def minimal_record(
    *,
    decision: Decision = "PAGAR",
    checks: list[CheckResult] | None = None,
    verifier: VerifierReport | None = None,
    admin_notice: str | None = None,
    jev_signals: list[JevSignal] | None = None,
    summary: str = (
        "Pagada: cumple todas las reglas (13 chequeos). Monto USD 1000, vence 2026-03-20."
    ),
    next_step: str = "Pago simulado registrado.",
) -> DecisionRecord:
    checks = checks if checks is not None else all_ok_checks()
    verifier = verifier if verifier is not None else make_verifier()
    jev_signals = jev_signals if jev_signals is not None else make_jev()
    return DecisionRecord.model_validate(
        {
            "id": "dec_gate_test",
            "invoice_id": "INV-GATE-001",
            "received_at": "2026-03-04T10:15:00Z",
            "decision": decision,
            "severity": SEVERITY[decision],
            "summary": summary,
            "extracted": {
                "beneficiary": "Globex LLC",
                "amount": 1000.0,
                "currency": "USD",
                "amount_base": 1000.0,
                "fx": {"rate": 1.0, "date": "2026-03-01"},
                "due_date": date(2026, 3, 20),
                "invoice_number": "GX-TEST-001",
                "recipient": "Acme Demo Inc.",
            },
            "checks": [c.model_dump(mode="json") for c in checks],
            "jev_signals": [s.model_dump(mode="json") for s in jev_signals],
            "verifier": verifier.model_dump(mode="json"),
            "admin_notice": admin_notice,
            "next_step": next_step,
            "trace": {"langsmith_run_id": "run_gate_test", "url": None},
            "versions": {
                "rules_version": "v1",
                "model_extractor": "extractor-demo",
                "model_verifier": "verifier-demo",
                "jev": "jev-1.13.0",
            },
            "human_events": [],
        }
    )
