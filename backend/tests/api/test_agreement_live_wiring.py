"""T9.1 (D061) §4 live wiring: the production pipeline must decide against the
EFFECTIVE rules (base + compiled active confirmed agreements), and a vendor
with an active, confirmed fixed-amount agreement must use its terms for
R06/contract lookup instead of `data/contracts/*.txt` -- no LLM contract call.

Fakes only for LLM/JEV (I7); the real graph, real rules engine, and a real
SQLite-backed `SqlStore` run end to end through the production app.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.api import create_app
from app.api.production_processor import make_production_processor
from app.config import Settings
from app.extraction.contracts import CONTRACT_EXTRACTOR_SYSTEM_PROMPT
from app.extraction.extract import EXTRACTOR_SYSTEM_PROMPT
from app.extraction.metered import METERED_EXTRACTOR_SYSTEM_PROMPT
from app.graph.deps import GraphDeps
from app.models.agreement import HourlyAgreement, OvertimeTerms, RetainerAgreement
from app.models.domain import JevSignal
from app.models.rules_config import AmountRange
from app.persistence import SqlStore, init_database, seed_rules
from app.rules.fx import load_fx_table
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import create_engine
from tests.api.support import (
    RULES_PATH,
    USER_HEADERS,
    load_approver_emails,
    load_approver_groups,
)

_CONFIRMED_AT = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIRMED_BY = "cfo@demo.test"


class _FakeExtractor:
    """Dispatches by system prompt (I7-safe: never trusts the document text)."""

    def __init__(self, invoice_payload: dict, metered_payload: dict | None = None) -> None:
        self._invoice_payload = invoice_payload
        self._metered_payload = metered_payload or {"metered_lines": []}
        self.calls: list[str] = []

    def complete_json(self, system: str, user: str) -> dict:
        del user
        self.calls.append(system)
        if system == EXTRACTOR_SYSTEM_PROMPT:
            return self._invoice_payload
        if system == METERED_EXTRACTOR_SYSTEM_PROMPT:
            return self._metered_payload
        if system == CONTRACT_EXTRACTOR_SYSTEM_PROMPT:
            raise AssertionError(
                "contract LLM lookup must never run for a vendor with an active "
                "confirmed agreement (T9.1 D061 §4)"
            )
        raise AssertionError(f"unexpected extractor prompt: {system[:40]!r}")


class _FakeVerifier:
    def complete_json(self, system: str, user: str) -> dict:
        del system, user
        return {"consistent": True, "issues": []}


class _FakeJev:
    def ask(self, state: str, questions) -> list[JevSignal]:
        del state, questions
        return [
            JevSignal(id="J1", answer=True, probability=0.99),
            JevSignal(id="J2", answer=True, probability=0.99),
            JevSignal(id="J3", answer=True, probability=0.99),
            JevSignal(id="J4", answer=True, probability=0.99),
            JevSignal(id="J5", answer="servicios", probability=0.99),
            JevSignal(id="J6", answer=True, probability=0.99),
            JevSignal(id="J7", answer=True, probability=0.99),
        ]


def _store(tmp_path: Path) -> SqlStore:
    db = tmp_path / "agreements.sqlite"
    engine = create_engine(f"sqlite:///{db}")
    init_database(engine)
    store = SqlStore(engine)
    seed_rules(store, RULES_PATH)
    return store


def _client(store: SqlStore, extractor: _FakeExtractor, *, contracts_dir: Path):
    fx_table = load_fx_table(RULES_PATH.resolve().parent / "fx.json")

    def deps_factory(settings: Settings, rules, ledger) -> GraphDeps:
        del settings  # fakes below never touch network settings
        return GraphDeps(
            extractor=extractor,
            verifier=_FakeVerifier(),
            jev=_FakeJev(),
            rules=rules,
            fx=fx_table,
            ledger=ledger,
            company_name=rules.company.name,
            rules_version="v-test",
            model_extractor="fake-extractor",
            model_verifier="fake-verifier",
            jev_label="fake-jev",
            # Empty, never populated with any vendor: proves a fixed-amount
            # agreement's R06 does not come from `data/contracts/*.txt`.
            contracts_dir=contracts_dir,
        )

    processor = make_production_processor(
        store, deps_factory=deps_factory, checkpointer=MemorySaver()
    )
    app = create_app(
        store,
        processor,
        clock=lambda: datetime(2026, 3, 15, 12, 0, tzinfo=UTC),
        rate_limit=1000,
        admin_api_key=None,
        approver_emails=load_approver_emails(),
        approver_groups=load_approver_groups(),
    )
    return TestClient(app, headers=USER_HEADERS)


def _post(client: TestClient, *, invoice_id: str, doc_text: str) -> dict:
    response = client.post(
        "/invoices",
        data={
            "invoice_id": invoice_id,
            "channel": "chat",
            # T5.13 follow-up: ignored as authoritative -- the server clock
            # (fixed above) decides the window; this is only ever metadata.
            "received_at": "2020-01-01T00:00:00Z",
        },
        files={"file": ("invoice.pdf", doc_text.encode("utf-8"), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _confirmed_fixed_retainer(store: SqlStore, vendor_name: str) -> None:
    agreement = RetainerAgreement(
        vendor_name=vendor_name,
        currency="USD",
        valid_from="2026-01-01",
        valid_to="2026-12-31",
        periodicity="monthly",
        amount=AmountRange(min=800.0, max=800.0),
    )
    store.confirm_agreement(
        agreement.vendor_key,
        terms=agreement,
        confirmed_by=_CONFIRMED_BY,
        expected_version=0,
        source_sha256=None,
        spans={},
        at=_CONFIRMED_AT,
    )


def _confirmed_hourly(store: SqlStore, vendor_name: str) -> None:
    agreement = HourlyAgreement(
        vendor_name=vendor_name,
        currency="USD",
        valid_from="2026-01-01",
        valid_to="2026-12-31",
        rate=25.0,
        included_hours=120.0,
        overtime=OvertimeTerms(multiplier=1.5),
    )
    store.confirm_agreement(
        agreement.vendor_key,
        terms=agreement,
        confirmed_by=_CONFIRMED_BY,
        expected_version=0,
        source_sha256=None,
        spans={},
        at=_CONFIRMED_AT,
    )


def test_confirmed_fixed_agreement_drives_r06_without_llm_contract_call(tmp_path) -> None:
    store = _store(tmp_path)
    _confirmed_fixed_retainer(store, "Globex LLC")

    doc_text = (
        "Factura\n"
        "Proveedor: Globex LLC\n"
        "Monto: 800 USD\n"
        "Vencimiento: 2026-03-15\n"
        "Numero: GLX-100\n"
        "Para: Acme Demo Inc.\n"
        "Departamento: Ingenieria\n"
    )
    extractor = _FakeExtractor(
        {
            "beneficiary": "Globex LLC",
            "amount": 800.0,
            "currency": "USD",
            "due_date": "2026-03-15",
            "invoice_number": "GLX-100",
            "recipient": "Acme Demo Inc.",
            "department": "Ingenieria",
            "invoice_type": None,
            "lines": [],
            "source_spans": {
                "beneficiary": "Proveedor: Globex LLC",
                "amount": "Monto: 800 USD",
                "currency": "Monto: 800 USD",
                "due_date": "Vencimiento: 2026-03-15",
                "invoice_number": "Numero: GLX-100",
                "recipient": "Para: Acme Demo Inc.",
                "department": "Departamento: Ingenieria",
            },
        }
    )
    client = _client(store, extractor, contracts_dir=tmp_path / "no-contracts-here")

    record = _post(client, invoice_id="INV-AGR-001", doc_text=doc_text)

    r06 = next(c for c in record["checks"] if c["rule"] == "R06")
    assert r06["result"] == "OK"
    # The LLM contract-extraction prompt was never invoked for this vendor.
    assert CONTRACT_EXTRACTOR_SYSTEM_PROMPT not in extractor.calls


def test_hourly_agreement_overbilling_frenar(tmp_path) -> None:
    """T9.1 §4 acceptance example: 128h, 120 included at USD 25 x1.5 ->
    expected USD 3300; billing USD 3600 -> R19 FALLA (on_fail FRENAR)."""
    store = _store(tmp_path)
    _confirmed_hourly(store, "Initech SAS")

    doc_text = (
        "Factura\n"
        "Proveedor: Initech SAS\n"
        "Horas trabajadas: 128 horas\n"
        "Monto: 3600 USD\n"
        "Vencimiento: 2026-04-01\n"
        "Numero: INIT-OVER-1\n"
        "Para: Acme Demo Inc.\n"
        "Departamento: Ingenieria\n"
    )
    extractor = _FakeExtractor(
        {
            "beneficiary": "Initech SAS",
            "amount": 3600.0,
            "currency": "USD",
            "due_date": "2026-04-01",
            "invoice_number": "INIT-OVER-1",
            "recipient": "Acme Demo Inc.",
            "department": "Ingenieria",
            "invoice_type": None,
            "lines": [],
            "source_spans": {
                "beneficiary": "Proveedor: Initech SAS",
                "amount": "Monto: 3600 USD",
                "currency": "Monto: 3600 USD",
                "due_date": "Vencimiento: 2026-04-01",
                "invoice_number": "Numero: INIT-OVER-1",
                "recipient": "Para: Acme Demo Inc.",
                "department": "Departamento: Ingenieria",
            },
        },
        metered_payload={
            "metered_lines": [
                {
                    "quantity": 128.0,
                    "unit": "hora",
                    "unit_rate": None,
                    "base_amount": None,
                    "line_amount": None,
                    "source_span": "128 horas",
                }
            ]
        },
    )
    client = _client(store, extractor, contracts_dir=tmp_path / "no-contracts-here")

    record = _post(client, invoice_id="INV-AGR-002", doc_text=doc_text)

    r19 = next(c for c in record["checks"] if c["rule"] == "R19")
    assert r19["result"] == "FALLA"
    assert r19["on_fail"] == "FRENAR"
    # FRENAR is the ceiling severity: once R19 fails FRENAR, the final
    # decision is FRENAR regardless of every other check's outcome.
    assert record["decision"] == "FRENAR"


def test_hourly_agreement_correct_billing_never_pays(tmp_path) -> None:
    """A *correctly* billed variable (hourly) agreement still has no single
    fixed amount for R06 to confirm -- T7.3's documented floor: ESCALAR,
    never PAGAR (T9.1 §4: "variable agreements always >= ESCALAR")."""
    store = _store(tmp_path)
    _confirmed_hourly(store, "Initech SAS")

    doc_text = (
        "Factura\n"
        "Proveedor: Initech SAS\n"
        "Horas trabajadas: 128 horas\n"
        "Monto: 3300 USD\n"
        "Vencimiento: 2026-04-01\n"
        "Numero: INIT-OK-1\n"
        "Para: Acme Demo Inc.\n"
        "Departamento: Ingenieria\n"
    )
    extractor = _FakeExtractor(
        {
            "beneficiary": "Initech SAS",
            "amount": 3300.0,
            "currency": "USD",
            "due_date": "2026-04-01",
            "invoice_number": "INIT-OK-1",
            "recipient": "Acme Demo Inc.",
            "department": "Ingenieria",
            "invoice_type": None,
            "lines": [],
            "source_spans": {
                "beneficiary": "Proveedor: Initech SAS",
                "amount": "Monto: 3300 USD",
                "currency": "Monto: 3300 USD",
                "due_date": "Vencimiento: 2026-04-01",
                "invoice_number": "Numero: INIT-OK-1",
                "recipient": "Para: Acme Demo Inc.",
                "department": "Departamento: Ingenieria",
            },
        },
        metered_payload={
            "metered_lines": [
                {
                    "quantity": 128.0,
                    "unit": "hora",
                    "unit_rate": None,
                    "base_amount": None,
                    "line_amount": None,
                    "source_span": "128 horas",
                }
            ]
        },
    )
    client = _client(store, extractor, contracts_dir=tmp_path / "no-contracts-here")

    record = _post(client, invoice_id="INV-AGR-003", doc_text=doc_text)

    r06 = next(c for c in record["checks"] if c["rule"] == "R06")
    assert r06["result"] == "INDETERMINADO"
    assert record["decision"] != "PAGAR"


def test_unknown_vendor_without_agreement_still_frenar(tmp_path) -> None:
    """Agreements never bypass R01: a vendor with no agreement and no
    allowlist entry is still FRENAR, exactly as without T9.1 at all."""
    store = _store(tmp_path)
    _confirmed_fixed_retainer(store, "Globex LLC")  # some other vendor has one

    doc_text = (
        "Factura\n"
        "Proveedor: Vendor Fantasma SAS\n"
        "Monto: 500 USD\n"
        "Vencimiento: 2026-03-20\n"
        "Numero: GHOST-1\n"
        "Para: Acme Demo Inc.\n"
        "Departamento: Ingenieria\n"
    )
    extractor = _FakeExtractor(
        {
            "beneficiary": "Vendor Fantasma SAS",
            "amount": 500.0,
            "currency": "USD",
            "due_date": "2026-03-20",
            "invoice_number": "GHOST-1",
            "recipient": "Acme Demo Inc.",
            "department": "Ingenieria",
            "invoice_type": None,
            "lines": [],
            "source_spans": {
                "beneficiary": "Proveedor: Vendor Fantasma SAS",
                "amount": "Monto: 500 USD",
                "currency": "Monto: 500 USD",
                "due_date": "Vencimiento: 2026-03-20",
                "invoice_number": "Numero: GHOST-1",
                "recipient": "Para: Acme Demo Inc.",
                "department": "Departamento: Ingenieria",
            },
        }
    )
    client = _client(store, extractor, contracts_dir=tmp_path / "no-contracts-here")

    record = _post(client, invoice_id="INV-AGR-004", doc_text=doc_text)

    r01 = next(c for c in record["checks"] if c["rule"] == "R01")
    assert r01["result"] == "FALLA"
    assert record["decision"] == "FRENAR"


def test_without_agreements_rules_are_byte_identical_to_base(tmp_path) -> None:
    """T9.1 §4: `compile_rules(base, [])` leaves `base` untouched -- the live
    pipeline with no agreements must behave exactly as before T9.1."""
    from app.api.production_processor import effective_rules_and_contracts

    store = _store(tmp_path)
    rules, contracts = effective_rules_and_contracts(store)
    assert rules == store.rules
    assert contracts == {}
