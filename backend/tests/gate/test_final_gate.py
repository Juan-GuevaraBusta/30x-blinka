"""T2.7 — run_final_gate orchestration, I2/I3, decide() integration (skipif)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from app.gate.final_gate import GateInput, run_final_gate
from app.models.domain import VerifierIssue
from conftest import (
    all_ok_checks,
    default_thresholds,
    make_check,
    make_jev,
    make_verifier,
    minimal_record,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
GATE_SRC = REPO_ROOT / "backend" / "app" / "gate"
FORBIDDEN_IMPORT_ROOTS = frozenset(
    {
        "langchain",
        "langgraph",
        "openai",
        "anthropic",
        "app.rules",
        "app.graph",
        "app.extraction",
        "app.jev",
        "app.verifier",
    }
)


def _run_gate(
    *,
    proposed: str,
    record,
    thresholds=None,
):
    return run_final_gate(
        GateInput(
            proposed_decision=proposed,
            record=record,
            jev_thresholds=thresholds or default_thresholds(),
        ),
    )


def test_happy_pagar() -> None:
    record = minimal_record(decision="PAGAR")
    out = _run_gate(proposed="PAGAR", record=record)
    assert out.final_decision == "PAGAR"
    assert out.gate_violations == []
    assert out.record.decision == "PAGAR"
    assert out.record.severity == 0


def test_pagar_with_falla_escalates_i1_checks() -> None:
    checks = all_ok_checks()
    checks[0] = make_check("R01", "FALLA", on_fail="FRENAR", detail="no permitido")
    record = minimal_record(
        decision="PAGAR",
        checks=checks,
        summary="Resumen sin citar reglas fallidas.",
    )
    out = _run_gate(proposed="PAGAR", record=record)
    assert out.final_decision == "ESCALAR"
    assert "I1_checks" in out.gate_violations
    assert out.record.decision == "ESCALAR"
    assert out.record.severity == 1


def test_pagar_with_low_jev_escalates_i1_jev() -> None:
    record = minimal_record(decision="PAGAR", jev_signals=make_jev(j2=0.5))
    out = _run_gate(proposed="PAGAR", record=record)
    assert out.final_decision == "ESCALAR"
    assert "I1_jev" in out.gate_violations


def test_pagar_inconsistent_verifier_escalates_i1_verifier() -> None:
    record = minimal_record(decision="PAGAR", verifier=make_verifier(consistent=False))
    out = _run_gate(proposed="PAGAR", record=record)
    assert out.final_decision == "ESCALAR"
    assert "I1_verifier" in out.gate_violations


def test_verifier_violation_without_notice_escalates_i5() -> None:
    report = make_verifier(
        consistent=False,
        issues=(VerifierIssue(code="V1", kind="violation", evidence="texto"),),
    )
    record = minimal_record(decision="PAGAR", verifier=report, admin_notice=None)
    out = _run_gate(proposed="PAGAR", record=record)
    assert out.final_decision == "ESCALAR"
    assert "I5_pending" in out.gate_violations
    assert out.final_decision != "PAGAR"


def test_verifier_violation_with_notice_frenar() -> None:
    report = make_verifier(
        consistent=False,
        issues=(VerifierIssue(code="V1", kind="violation", evidence="texto"),),
    )
    notice = "Se frenó la factura INV-GATE-001 de Globex LLC: hallazgo. Evidencia: texto."
    record = minimal_record(decision="FRENAR", verifier=report, admin_notice=notice)
    out = _run_gate(proposed="PAGAR", record=record)
    assert out.final_decision == "FRENAR"
    assert out.gate_violations == []
    assert out.record.decision == "FRENAR"


def test_proposed_frenar_not_lowered_by_verifier() -> None:
    record = minimal_record(
        decision="FRENAR",
        admin_notice="Aviso sintético al administrador.",
        summary="Frenada: beneficiario no permitido (regla R01).",
        checks=[make_check("R01", "FALLA", on_fail="FRENAR")],
    )
    out = _run_gate(proposed="FRENAR", record=record)
    assert out.final_decision == "FRENAR"


def test_proposed_frenar_without_notice_escalates_i5() -> None:
    record = minimal_record(
        decision="FRENAR",
        admin_notice=None,
        summary="Frenada: beneficiario no permitido (regla R01).",
        checks=[make_check("R01", "FALLA", on_fail="FRENAR")],
    )
    out = _run_gate(proposed="FRENAR", record=record)
    assert out.final_decision == "ESCALAR"
    assert "I5_pending" in out.gate_violations


def test_explanation_gap_escalates() -> None:
    checks = all_ok_checks()
    checks[3] = make_check("R04", "FALLA", on_fail="ESCALAR", detail="umbral")
    record = minimal_record(
        decision="ESCALAR",
        checks=checks,
        summary="Escalada sin citar la regla que falló.",
    )
    out = _run_gate(proposed="ESCALAR", record=record)
    assert out.final_decision == "ESCALAR"
    assert "explanation_gap" in out.gate_violations


def test_i3_violation_mentions_invariante_violado() -> None:
    record = minimal_record(decision="PAGAR", verifier=make_verifier(consistent=False))
    out = _run_gate(proposed="PAGAR", record=record)
    assert out.gate_violations
    text = out.record.summary + out.record.next_step
    assert "invariante_violado" in text


@pytest.mark.parametrize("path", sorted(GATE_SRC.glob("*.py")), ids=lambda p: p.name)
def test_i2_gate_modules_forbid_llm_and_rules_imports(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root not in FORBIDDEN_IMPORT_ROOTS
                assert alias.name not in FORBIDDEN_IMPORT_ROOTS
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            assert root not in FORBIDDEN_IMPORT_ROOTS
            assert node.module not in FORBIDDEN_IMPORT_ROOTS


def test_gate_with_decide() -> None:
    decide_mod = pytest.importorskip(
        "app.rules.decide",
        reason="decide() not implemented yet (T2.5)",
    )
    if not hasattr(decide_mod, "decide"):
        pytest.skip("decide() not implemented yet (T2.5)")
    checks = all_ok_checks()
    checks[1] = make_check("R02", "FALLA", on_fail="ESCALAR")
    proposed = decide_mod.decide(checks)
    record = minimal_record(decision=proposed, checks=checks)
    out = _run_gate(proposed=proposed, record=record)
    assert out.final_decision != "PAGAR"
