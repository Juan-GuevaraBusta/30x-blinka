"""T3.10 — Fail-closed fakes on the invoice graph (I3)."""

from __future__ import annotations

import socket
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.graph.deps import GraphDeps
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

_SOCKET_CALLS: list[tuple[Any, ...]] = []


class _SocketGuard(socket.socket):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        _SOCKET_CALLS.append(args)
        raise OSError("network blocked during graph import in T3.10")


_old_socket = socket.socket
socket.socket = _SocketGuard  # type: ignore[misc, assignment]
from app.graph import run_invoice  # noqa: E402

socket.socket = _old_socket

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


def _extraction_payload(doc: str, *, beneficiary: str = "Demo SA") -> dict[str, Any]:
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


def _contract_payload() -> dict[str, Any]:
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


def _jev_signals(*, probability: float = 0.99) -> list[JevSignal]:
    return [
        JevSignal(id="J1", answer=True, probability=probability),
        JevSignal(id="J2", answer=True, probability=probability),
        JevSignal(id="J3", answer=True, probability=probability),
        JevSignal(id="J4", answer=True, probability=probability),
        JevSignal(id="J5", answer="servicios", probability=probability),
        JevSignal(id="J6", answer=True, probability=probability),
        JevSignal(id="J7", answer=True, probability=probability),
    ]


class HappyExtractor:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        self.calls.append({"system": system, "user": user})
        if user.strip() == CONTRACT_TEXT.strip():
            return _contract_payload()
        return _extraction_payload(user)


class BrokenExtractor:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        self.calls.append({"system": system, "user": user})
        raise DecisionClientError(_SECRET)


class NonDictFirstExtractor:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def complete_json(self, system: str, user: str) -> Any:
        self.calls.append({"system": system, "user": user})
        if len(self.calls) == 1:
            return ["no-es-objeto"]
        if user.strip() == CONTRACT_TEXT.strip():
            return _contract_payload()
        return _extraction_payload(user)


class HappyVerifier:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        self.calls.append({"system": system, "user": user})
        return {"consistent": True, "issues": []}


class NonDictVerifier:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def complete_json(self, system: str, user: str) -> Any:
        self.calls.append({"system": system, "user": user})
        return ["no-es-objeto"]


class HappyJev:
    def __init__(self, *, probability: float = 0.99) -> None:
        self.calls: list[tuple[str, Sequence[JevQuestion]]] = []
        self._signals = _jev_signals(probability=probability)

    def ask(self, state: str, questions: Sequence[JevQuestion]) -> list[JevSignal]:
        self.calls.append((state, tuple(questions)))
        return list(self._signals)


class ExpiredJev:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Sequence[JevQuestion]]] = []

    def ask(self, state: str, questions: Sequence[JevQuestion]) -> list[JevSignal]:
        self.calls.append((state, tuple(questions)))
        raise DecisionClientError("http_error")


def _deps(
    tmp_path: Path,
    *,
    extractor: object,
    verifier: object,
    jev: object,
) -> GraphDeps:
    contract_path = tmp_path / "demo-sa.txt"
    contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
    return GraphDeps(
        extractor=extractor,
        verifier=verifier,
        jev=jev,
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
    thread_id: str,
) -> object:
    saver = MemorySaver()
    return run_invoice(
        deps,
        raw=PAY_CHAT.encode("utf-8"),
        channel="chat",
        invoice_id="INV-G1",
        received_at=datetime(2026, 3, 15, 12, 0, tzinfo=UTC),
        checkpointer=saver,
        thread_id=thread_id,
        tracer=None,
    )


def _assert_technical_escalar(record: object) -> None:
    assert record.decision == "ESCALAR"
    assert record.severity == 1
    assert "error_tecnico" in record.summary
    assert record.admin_notice is None
    assert record.decision != "PAGAR"
    assert record.trace.langsmith_run_id is None


def test_import_run_invoice_no_socket() -> None:
    assert _SOCKET_CALLS == []
    assert callable(run_invoice)


def test_llm_broken_escalar_no_secret_leak(tmp_path: Path) -> None:
    ext = BrokenExtractor()
    deps = _deps(tmp_path, extractor=ext, verifier=HappyVerifier(), jev=HappyJev())
    record = _run(deps, thread_id="t-fc-llm")
    _assert_technical_escalar(record)
    blob = f"{record.summary}{record.next_step}"
    assert _SECRET not in blob
    assert PAY_CHAT.strip() not in blob
    assert len(ext.calls) >= 1


def test_extractor_non_dict_json_escalar_verifier_not_called(tmp_path: Path) -> None:
    ext = NonDictFirstExtractor()
    ver = HappyVerifier()
    deps = _deps(tmp_path, extractor=ext, verifier=ver, jev=HappyJev())
    record = _run(deps, thread_id="t-fc-json-ext")
    _assert_technical_escalar(record)
    assert ver.calls == []


def test_jev_expired_escalar_verifier_not_called(tmp_path: Path) -> None:
    ext = HappyExtractor()
    ver = HappyVerifier()
    jev = ExpiredJev()
    deps = _deps(tmp_path, extractor=ext, verifier=ver, jev=jev)
    record = _run(deps, thread_id="t-fc-jev")
    _assert_technical_escalar(record)
    assert len(ext.calls) >= 2
    assert ver.calls == []
    assert "http_error" not in record.summary
    assert _SECRET not in f"{record.summary}{record.next_step}"


def test_verifier_non_dict_json_escalar_not_pagar(tmp_path: Path) -> None:
    ext = HappyExtractor()
    ver = NonDictVerifier()
    deps = _deps(tmp_path, extractor=ext, verifier=ver, jev=HappyJev())
    record = _run(deps, thread_id="t-fc-json-ver")
    _assert_technical_escalar(record)
    assert len(ver.calls) >= 1


def test_low_jev_probability_escalar_r09_no_error_tecnico(tmp_path: Path) -> None:
    deps = _deps(
        tmp_path,
        extractor=HappyExtractor(),
        verifier=HappyVerifier(),
        jev=HappyJev(probability=0.1),
    )
    record = _run(deps, thread_id="t-fc-r09")
    assert record.decision == "ESCALAR"
    assert record.decision != "PAGAR"
    assert record.admin_notice is None
    assert "error_tecnico" not in record.summary
    r09 = next(c for c in record.checks if c.rule == "R09")
    assert r09.result != "OK"
