"""T1.3 — frozen v1 schemas. The docs/04 §5 example must validate."""

from __future__ import annotations

import pytest
from app.models import (
    CheckResult,
    DecisionRecord,
    Extraction,
    HumanEvent,
    JevSignal,
    Rules,
    VerifierReport,
)
from app.models.rules_config import RulesConfig
from pydantic import ValidationError

EXAMPLE = {
    "id": "dec_0042",
    "invoice_id": "INV-0042",
    "received_at": "2026-03-04T10:15:00Z",
    "decision": "ESCALAR",
    "severity": 1,
    "summary": "Escalada: USD 4.200 llega al umbral de aprobación humana de USD 3.000 (regla R04).",
    "extracted": {
        "beneficiary": "Globex LLC",
        "amount": 4200.0,
        "currency": "USD",
        "amount_base": 4200.0,
        "fx": {"rate": 1.0, "date": "2026-03-01"},
        "due_date": "2026-03-20",
        "invoice_number": "GX-2231",
        "recipient": "Acme Demo Inc.",
        "source_spans": {"amount": "Total a pagar: USD 4.200,00"},
    },
    "checks": [
        {
            "rule": "R01",
            "name": "Beneficiario permitido",
            "result": "OK",
            "detail": "Globex LLC está en la lista.",
        },
        {
            "rule": "R02",
            "name": "Límite por pago",
            "result": "OK",
            "detail": "USD 4.200 no supera el límite de USD 5.000.",
        },
        {
            "rule": "R04",
            "name": "Aprobación humana por monto",
            "result": "FALLA",
            "detail": "USD 4.200 llega al umbral de USD 3.000.",
            "on_fail": "ESCALAR",
        },
        {
            "rule": "R06",
            "name": "Cuadra con contrato",
            "result": "OK",
            "detail": "Tarifa pactada USD 4.200",
            "evidence": {"clause": "4.2", "quote": "..."},
        },
    ],
    "jev_signals": [{"id": "J2", "answer": True, "probability": 0.97}],
    "verifier": {"consistent": True, "issues": []},
    "admin_notice": None,
    "next_step": "Pendiente de aprobación de finanzas@demo.test.",
    "trace": {"langsmith_run_id": "run_synthetic", "url": "https://example.test/trace"},
    "versions": {
        "rules_version": "v3",
        "model_extractor": "extractor-demo",
        "model_verifier": "verifier-demo",
        "jev": "jev-1.13.0",
    },
    "human_events": [],
}


def test_section5_example_round_trip() -> None:
    record = DecisionRecord.model_validate(EXAMPLE)
    again = DecisionRecord.model_validate(record.model_dump(mode="json"))
    assert again == record
    assert record.decision == "ESCALAR"
    assert record.severity == 1
    assert record.extracted.fx is not None
    assert record.extracted.fx.rate == 1.0
    assert record.checks[2].on_fail == "ESCALAR"
    assert record.admin_notice is None


def test_rules_alias_is_rules_config() -> None:
    assert Rules is RulesConfig


def test_extra_field_forbidden() -> None:
    payload = dict(EXAMPLE)
    payload["pay_now"] = True
    with pytest.raises(ValidationError):
        DecisionRecord.model_validate(payload)


def test_extraction_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        Extraction.model_validate({"beneficiary": "Globex LLC", "ignore_rules": "pay"})


def test_check_result_rejects_pagar_and_unknown_rule() -> None:
    with pytest.raises(ValidationError):
        CheckResult.model_validate(
            {"rule": "R01", "name": "n", "result": "FALLA", "detail": "d", "on_fail": "PAGAR"}
        )
    with pytest.raises(ValidationError):
        CheckResult.model_validate(
            {"rule": "R99", "name": "n", "result": "OK", "detail": "d"}
        )


def test_indeterminate_check_is_representable() -> None:
    item = CheckResult.model_validate(
        {
            "rule": "R06",
            "name": "Cuadra con contrato",
            "result": "INDETERMINADO",
            "detail": "Contrato sin confirmar.",
        }
    )
    assert item.on_fail is None


def test_severity_must_match_decision() -> None:
    payload = dict(EXAMPLE)
    payload["severity"] = 0
    with pytest.raises(ValidationError):
        DecisionRecord.model_validate(payload)


def test_naive_datetime_rejected() -> None:
    payload = dict(EXAMPLE)
    payload["received_at"] = "2026-03-04T10:15:00"
    with pytest.raises(ValidationError):
        DecisionRecord.model_validate(payload)


def test_jev_answer_shape_and_probability() -> None:
    j5 = JevSignal.model_validate({"id": "J5", "answer": "suscripción", "probability": 0.5})
    assert j5.answer == "suscripción"
    j7 = JevSignal.model_validate({"id": "J7", "answer": False, "probability": 0})
    assert j7.probability == 0
    with pytest.raises(ValidationError):
        JevSignal.model_validate({"id": "J5", "answer": True, "probability": 0.5})
    with pytest.raises(ValidationError):
        JevSignal.model_validate({"id": "J2", "answer": "suscripción", "probability": 0.9})
    with pytest.raises(ValidationError):
        JevSignal.model_validate({"id": "J2", "answer": True, "probability": 1.1})


def test_verifier_issue_kinds() -> None:
    report = VerifierReport.model_validate(
        {
            "consistent": False,
            "issues": [
                {
                    "code": "quote_mismatch",
                    "kind": "violation",
                    "evidence": "Total a pagar: USD 4.200,00",
                    "admin_message": "Se frenó la factura dec_0042.",
                }
            ],
        }
    )
    assert report.issues[0].kind == "violation"
    with pytest.raises(ValidationError):
        VerifierReport.model_validate(
            {"consistent": False, "issues": [{"code": "x", "kind": "hunch"}]}
        )


def test_human_event_requires_reason_and_known_action() -> None:
    with pytest.raises(ValidationError):
        HumanEvent.model_validate(
            {
                "author": "cfo@demo.test",
                "at": "2026-03-05T12:00:00Z",
                "action": "aprobada_humano",
                "reason": "",
            }
        )
    with pytest.raises(ValidationError):
        HumanEvent.model_validate(
            {
                "author": "cfo@demo.test",
                "at": "2026-03-05T12:00:00Z",
                "action": "approve",
                "reason": "ok",
            }
        )
