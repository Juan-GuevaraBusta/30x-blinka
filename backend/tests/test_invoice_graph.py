"""T3.7 — LangGraph invoice graph (fail-closed wiring)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.graph import (
    GraphDeps,
    GraphError,
    InvoiceState,
    compile_invoice_graph,
    run_invoice,
)
from app.jev.decision_client import JevQuestion
from app.llm import DecisionClientError
from app.models.domain import JevSignal
from app.models.rules_config import (
    CompanyRef,
    JevThresholds,
    Limits,
    OnFail,
    PeriodLimit,
    RulesConfig,
)
from app.rules.fx import FxTable
from langgraph.checkpoint.memory import MemorySaver

PAY_CHAT = """Factura Demo SA
Total: 100 USD
Vence: 2026-04-01
Para: Blinka Demo
Depto: IT
Numero: INV-G1
"""

CONTRACT_TEXT = """confirmed: true
El beneficiario autorizado es Demo SA.
Cláusula 4.1. Tarifa 100 USD.
"""

_SECRET = "test-key"


def _minimal_rules() -> RulesConfig:
    return RulesConfig(
        company=CompanyRef(name="Blinka Demo", base_currency="USD"),
        limits=Limits(
            per_payment=5000,
            per_period=PeriodLimit(type="calendar_month", amount=100000),
        ),
        human_approval_threshold=3000,
        allowed_beneficiaries=["Demo SA"],
        department_budgets={"IT": 10000},
        approvers={"default": "a@demo.test"},
        manual_blocks=[],
        on_fail=OnFail(
            R01="FRENAR",
            R02="ESCALAR",
            R03="ESCALAR",
            R04="ESCALAR",
            R05="FRENAR",
            R06="ESCALAR",
            R07="FRENAR",
            R08="ESCALAR",
            R09="ESCALAR",
            R10="ESCALAR",
            R11="ESCALAR",
            R12="ESCALAR",
            R13="ESCALAR",
        ),
        jev_thresholds=JevThresholds(J1=0.5, J2=0.5, J3=0.5, J4=0.5, J6=0.5, J7=0.5),
    )


def _fx() -> FxTable:
    from datetime import date

    return FxTable(as_of=date(2026, 3, 1), base_currency="USD", quote="USD", rates={"USD": 1.0})


def _extraction_payload(doc: str, *, beneficiary: str = "Demo SA") -> dict:
    return {
        "beneficiary": beneficiary,
        "amount": 100.0,
        "currency": "USD",
        "due_date": "2026-04-01",
        "invoice_number": "INV-G1",
        "recipient": "Blinka Demo",
        "department": "IT",
        "invoice_type": None,
        "lines": [],
        "source_spans": {
            "beneficiary": beneficiary,
            "amount": "100 USD",
            "currency": "100 USD",
            "due_date": "2026-04-01",
            "invoice_number": "INV-G1",
            "recipient": "Blinka Demo",
            "department": "IT",
        },
    }


def _contract_payload() -> dict:
    return {
        "beneficiary": "Demo SA",
        "fee_amount": 100.0,
        "fee_currency": "USD",
        "period_cap_amount": None,
        "period_cap_currency": None,
        "billing_period": None,
        "cited_clauses": ["4.1"],
        "quotes": {
            "beneficiary": "El beneficiario autorizado es Demo SA.",
            "fee_amount": "100 USD",
            "fee_currency": "100 USD",
        },
    }


def _jev_signals() -> list[JevSignal]:
    return [
        JevSignal(id="J1", answer=True, probability=0.99),
        JevSignal(id="J2", answer=True, probability=0.99),
        JevSignal(id="J3", answer=True, probability=0.99),
        JevSignal(id="J4", answer=True, probability=0.99),
        JevSignal(id="J5", answer="servicios", probability=0.99),
        JevSignal(id="J6", answer=True, probability=0.99),
        JevSignal(id="J7", answer=True, probability=0.99),
    ]


class RoutingExtractor:
    def __init__(
        self,
        *,
        error: Exception | None = None,
        beneficiary: str = "Demo SA",
    ) -> None:
        self.calls: list[dict[str, str]] = []
        self._error = error
        self._beneficiary = beneficiary

    def complete_json(self, system: str, user: str) -> dict:
        self.calls.append({"system": system, "user": user})
        if self._error is not None:
            raise self._error
        if user.strip() == CONTRACT_TEXT.strip():
            return _contract_payload()
        return _extraction_payload(user, beneficiary=self._beneficiary)


class FakeVerifier:
    def __init__(self, response: dict | None = None, *, error: Exception | None = None) -> None:
        self.calls: list[dict[str, str]] = []
        self._response = response or {"consistent": True, "issues": []}
        self._error = error

    def complete_json(self, system: str, user: str) -> dict:
        self.calls.append({"system": system, "user": user})
        if self._error is not None:
            raise self._error
        return self._response


class FakeJev:
    def __init__(self, signals: list[JevSignal] | None = None) -> None:
        self.calls: list[tuple[str, Sequence[JevQuestion]]] = []
        self._signals = signals or _jev_signals()

    def ask(self, state: str, questions: Sequence[JevQuestion]) -> list[JevSignal]:
        self.calls.append((state, tuple(questions)))
        return list(self._signals)


def _deps(
    tmp_path: Path,
    *,
    extractor: RoutingExtractor | None = None,
    verifier: FakeVerifier | None = None,
    beneficiary: str = "Demo SA",
) -> GraphDeps:
    contract_path = tmp_path / "demo-sa.txt"
    contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
    ext = extractor or RoutingExtractor(beneficiary=beneficiary)
    ver = verifier or FakeVerifier()
    return GraphDeps(
        extractor=ext,
        verifier=ver,
        jev=FakeJev(),
        rules=_minimal_rules(),
        fx=_fx(),
        ledger=(),
        company_name="Blinka Demo",
        rules_version="test-rules",
        model_extractor="fake-extractor",
        model_verifier="fake-verifier",
        jev_label="fake-jev",
        contracts_dir=tmp_path,
    )


def _run(
    deps: GraphDeps,
    *,
    raw: bytes | None = None,
    channel: str = "chat",
    thread_id: str = "t-default",
) -> tuple[object, MemorySaver]:
    saver = MemorySaver()
    record = run_invoice(
        deps,
        raw=raw or PAY_CHAT.encode("utf-8"),
        channel=channel,  # type: ignore[arg-type]
        invoice_id="INV-G1",
        received_at=datetime(2026, 3, 15, 12, 0, tzinfo=UTC),
        checkpointer=saver,
        thread_id=thread_id,
    )
    return record, saver


def test_graph_error_empty_invoice_id(tmp_path: Path) -> None:
    deps = _deps(tmp_path)
    ext = deps.extractor
    saver = MemorySaver()
    with pytest.raises(GraphError) as exc:
        run_invoice(
            deps,
            raw=PAY_CHAT.encode(),
            channel="chat",
            invoice_id="   ",
            received_at=datetime(2026, 3, 15, 12, 0, tzinfo=UTC),
            checkpointer=saver,
            thread_id="t-err",
        )
    assert exc.value.code == "empty_invoice_id"
    assert str(exc.value) == "empty_invoice_id"
    assert ext.calls == []


def test_graph_error_naive_datetime(tmp_path: Path) -> None:
    deps = _deps(tmp_path)
    ext = deps.extractor
    saver = MemorySaver()
    with pytest.raises(GraphError) as exc:
        run_invoice(
            deps,
            raw=PAY_CHAT.encode(),
            channel="chat",
            invoice_id="INV-G1",
            received_at=datetime(2026, 3, 15, 12, 0),
            checkpointer=saver,
            thread_id="t-err",
        )
    assert exc.value.code == "naive_datetime"
    assert ext.calls == []


def test_illegible_image_no_llm(tmp_path: Path) -> None:
    deps = _deps(tmp_path)
    record, _ = _run(deps, raw=b"not-an-image", channel="image")
    assert record.decision == "ESCALAR"
    assert "documento ilegible" in record.summary
    assert deps.extractor.calls == []
    assert deps.jev.calls == []


def test_extractor_exception_escalar(tmp_path: Path) -> None:
    ext = RoutingExtractor(error=DecisionClientError(_SECRET))
    deps = _deps(tmp_path, extractor=ext)
    record, _ = _run(deps)
    assert record.decision == "ESCALAR"
    assert record.severity == 1
    assert "error_tecnico" in record.summary
    assert record.admin_notice is None
    blob = f"{record.summary}{record.next_step}"
    assert _SECRET not in blob
    assert PAY_CHAT.strip() not in blob


def test_happy_path_pagar_and_checkpointer(tmp_path: Path) -> None:
    deps = _deps(tmp_path)
    record, saver = _run(deps, thread_id="t-pagar")
    assert record.decision == "PAGAR"
    assert record.severity == 0
    assert len(record.checks) == 13
    assert all(c.result == "OK" for c in record.checks)
    assert record.verifier.consistent is True
    assert record.trace.langsmith_run_id is None
    graph = compile_invoice_graph(deps, saver)
    state = graph.get_state({"configurable": {"thread_id": "t-pagar"}})
    assert state.values["final_decision"] == "PAGAR"


def test_verifier_violation_frenar_admin_notice(tmp_path: Path) -> None:
    verifier = FakeVerifier(
        {
            "consistent": False,
            "issues": [
                {
                    "code": "extraction_mismatch",
                    "kind": "violation",
                    "evidence": "100 USD",
                    "admin_message": "Monto no coincide",
                }
            ],
        }
    )
    deps = _deps(tmp_path, verifier=verifier)
    record, _ = _run(deps)
    assert record.decision == "FRENAR"
    assert record.admin_notice is not None
    assert "100 USD" in record.admin_notice


def test_verifier_uncertainty_escalar_no_notice(tmp_path: Path) -> None:
    verifier = FakeVerifier(
        {
            "consistent": False,
            "issues": [
                {
                    "code": "unclear",
                    "kind": "uncertainty",
                    "evidence": None,
                    "admin_message": None,
                }
            ],
        }
    )
    deps = _deps(tmp_path, verifier=verifier)
    record, _ = _run(deps)
    assert record.decision == "ESCALAR"
    assert record.admin_notice is None


def test_r01_frenar_not_lowered_by_clean_verifier(tmp_path: Path) -> None:
    doc = PAY_CHAT.replace("Demo SA", "Fuera De Lista", 1)
    ext = RoutingExtractor(beneficiary="Fuera De Lista")
    deps = _deps(tmp_path, extractor=ext, beneficiary="Fuera De Lista")
    record, _ = _run(deps, raw=doc.encode())
    assert record.decision == "FRENAR"


def test_frenar_preserved_when_verifier_raises(tmp_path: Path) -> None:
    doc = PAY_CHAT.replace("Demo SA", "Fuera De Lista", 1)
    ext = RoutingExtractor(beneficiary="Fuera De Lista")
    verifier = FakeVerifier(error=DecisionClientError(_SECRET))
    deps = _deps(tmp_path, extractor=ext, verifier=verifier, beneficiary="Fuera De Lista")
    record, _ = _run(deps, raw=doc.encode())
    assert record.decision == "FRENAR"
    assert record.admin_notice is not None


def test_graph_compiled_nodes_include_escalate(tmp_path: Path) -> None:
    deps = _deps(tmp_path)
    graph = compile_invoice_graph(deps, MemorySaver())
    names = set(graph.get_graph().nodes)
    expected = {
        "ingest",
        "extract",
        "contract_lookup",
        "jev_checks",
        "det_checks",
        "aggregate",
        "record",
        "verify",
        "final_gate",
        "escalate_technical",
        "__start__",
        "__end__",
    }
    assert expected <= names


def test_public_import_has_no_side_effects() -> None:
    from app.graph import compile_invoice_graph, run_invoice

    assert callable(compile_invoice_graph)
    assert callable(run_invoice)
    assert InvoiceState is not None
