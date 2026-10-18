"""Wire HTTP invoice upload to LangGraph (G4). Rules come from the live store."""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from app.api.schemas import InvoiceRejected, InvoiceUpload
from app.api.tenancy import (
    CURRENT_COMPANY,
    DEMO_COMPANY_ID,
    Company,
    fallback_rules,
    with_company_identity,
)
from app.config import Settings, load_settings, resolve_backend
from app.extraction.ingest import IngestChannel
from app.graph.build import GraphError, run_invoice
from app.graph.deps import GraphDeps
from app.graph.folder_batch import RULES_VERSION, repo_root_from_module
from app.graph.tracing import NullTrace, TraceSession
from app.jev.decision_client import build_decision_client
from app.llm import HttpTransport, get_llm, model_for_role
from app.models.domain import DecisionRecord
from app.models.rules_config import RulesConfig
from app.persistence.sql_store import SqlStore
from app.rules.agreements import (
    AgreementConflictError,
    agreement_contract_map,
    compile_rules,
)
from app.rules.context import ContractTerms, LedgerEntry
from app.rules.fx import FxTable, load_fx_table, rebase_fx_table
from app.rules.ledger import Ledger
from app.rules.settlement import settlement_amount_base

_logger = logging.getLogger(__name__)

Processor = Callable[[InvoiceUpload, str], DecisionRecord]
DepsFactory = Callable[[Settings, RulesConfig, tuple[LedgerEntry, ...]], GraphDeps]

_PROCESS_CHECKPOINTER = MemorySaver()


def _approval_ledger_line(record: DecisionRecord, fx: FxTable) -> LedgerEntry | None:
    """One line per approved decision, however many approval events it has.

    Several approvers on one decision (T7.1 «x de N») approve a single payment:
    counting one line per event double-counted its amount in R03/R07/R21.
    The latest approval time is used: R20 ("an approval after added_at")
    gives the same answer as with one line per event, and 30-day windows
    (R05/R21) keep the line in view the longest. A later rejection does not
    remove the line (conservative, unchanged from the per-event behavior).
    """
    approvals = [e for e in record.human_events if e.action == "aprobada_humano"]
    if not approvals:
        return None
    event = max(approvals, key=lambda e: e.at)
    ext = record.extracted
    beneficiary = (ext.beneficiary or "").strip()
    if not beneficiary:
        return None
    at = event.at
    received_at = (
        at.isoformat().replace("+00:00", "Z") if isinstance(at, datetime) else str(at)
    )
    return LedgerEntry(
        beneficiary=beneficiary,
        amount_base=settlement_amount_base(ext, fx),
        currency=ext.currency or "USD",
        invoice_number=ext.invoice_number or "",
        received_at=received_at,
        decision="aprobada_humano",
        department=ext.department,
        due_date=ext.due_date.isoformat() if ext.due_date else None,
    )


def _record_settlement(record: DecisionRecord, fx: FxTable) -> LedgerEntry | None:
    if record.decision != "PAGAR":
        return None
    ext = record.extracted
    received = record.received_at
    if isinstance(received, datetime):
        received_at = received.isoformat().replace("+00:00", "Z")
    else:
        received_at = str(received)
    return LedgerEntry(
        beneficiary=ext.beneficiary or "",
        amount_base=settlement_amount_base(ext, fx),
        currency=ext.currency or "USD",
        invoice_number=ext.invoice_number or "",
        received_at=received_at,
        decision="PAGAR",
        department=ext.department,
        due_date=ext.due_date.isoformat() if ext.due_date else None,
    )


def _company_decisions(store: SqlStore, company_id: str) -> dict[str, DecisionRecord]:
    """T9.8: only this company's decisions feed its ledger. Duck-typed stores
    without `decisions_for` (test doubles) expose a single tenant."""
    decisions_for = getattr(store, "decisions_for", None)
    if decisions_for is None:
        return store.decisions
    return decisions_for(company_id)


def settled_ledger_from_store(
    store: SqlStore, fx: FxTable | None = None, *, company_id: str = DEMO_COMPANY_ID
) -> Ledger:
    """Prior PAGAR lines and human approvals already persisted (T7.4 R20).

    T5.13 (D063): ``amount_base`` is recomputed from amount + currency with the
    fixed FX table; an unconvertible amount is stored as ``None``, never 0.0.
    """
    table = fx if fx is not None else load_fx_table()
    settled = Ledger.empty()
    for record in _company_decisions(store, company_id).values():
        settlement = _record_settlement(record, table)
        if settlement is not None:
            settled = settled.record_settlement(settlement, invoice_id=record.invoice_id)
        approval = _approval_ledger_line(record, table)
        if approval is not None:
            tie = f"{record.invoice_id}:aprobada:{record.id}"
            settled = settled.record_settlement(approval, invoice_id=tie)
    return settled


def _pending_ledger_line(record: DecisionRecord, fx: FxTable) -> LedgerEntry | None:
    """One line for a decision still awaiting a human call.

    P0 safety fix: ``ESCALAR`` with no human event yet (not approved, not
    rejected). A decision with an ``aprobada_humano`` event is already a
    settlement (``_approval_ledger_line`` covers it) even though ``decision``
    stays ``ESCALAR`` forever (I2); a ``rechazada_humano`` event means the
    invoice was rejected, not pending. Only used by R05 (duplicate-of-pending):
    never fed into ``Ledger``/``settled_ledger_from_store``, so it can never
    be counted by R03/R07/R17/R21.
    """
    if record.decision != "ESCALAR":
        return None
    decided = ("aprobada_humano", "rechazada_humano")
    if any(event.action in decided for event in record.human_events):
        return None
    ext = record.extracted
    beneficiary = (ext.beneficiary or "").strip()
    if not beneficiary:
        return None
    received = record.received_at
    if isinstance(received, datetime):
        received_at = received.isoformat().replace("+00:00", "Z")
    else:
        received_at = str(received)
    return LedgerEntry(
        beneficiary=beneficiary,
        amount_base=settlement_amount_base(ext, fx),
        currency=ext.currency or "USD",
        invoice_number=ext.invoice_number or "",
        received_at=received_at,
        decision="ESCALAR",
        department=ext.department,
        due_date=ext.due_date.isoformat() if ext.due_date else None,
    )


def pending_ledger_from_store(
    store: SqlStore, fx: FxTable | None = None, *, company_id: str = DEMO_COMPANY_ID
) -> tuple[LedgerEntry, ...]:
    """Decisions still awaiting a human call (R05 duplicate-of-pending only).

    P0 safety fix: an invoice resubmitted while the first copy is still
    ``ESCALAR`` previously escaped R05 entirely, because duplicate detection
    only ever looked at ``settled_ledger_from_store`` (PAGAR/approved). Never
    merge this into the settled ``Ledger``: a pending invoice has not been
    approved or paid, so it must never consume an R03/R07/R17/R21 budget.
    """
    table = fx if fx is not None else load_fx_table()
    lines: list[LedgerEntry] = []
    for record in _company_decisions(store, company_id).values():
        line = _pending_ledger_line(record, table)
        if line is not None:
            lines.append(line)
    return tuple(lines)


def ledger_view_for_upload(upload: InvoiceUpload, prior: Ledger) -> tuple[LedgerEntry, ...]:
    """Every persisted settlement, regardless of the client-supplied ``received_at``.

    T5.13 (D063): everything in the store was already processed in real time, so
    the whole history is "before" this upload. Filtering by the client's date let
    a backdated resubmission hide the original payment from R05.
    """
    del upload  # the view no longer depends on the (untrusted) client date
    return prior.as_tuple()


def effective_rules_and_contracts(
    store: SqlStore, *, company_id: str = DEMO_COMPANY_ID
) -> tuple[RulesConfig, dict[str, ContractTerms]]:
    """T9.1 (D061) §4: the rules the live pipeline must use -- `store.rules`
    (base, hand-edited) plus every active, confirmed vendor agreement
    compiled in on top -- and the vendor_key -> fixed-amount contract-terms
    map the graph's `contract_lookup` node uses instead of `data/contracts/*.txt`.

    Same `GET /rules/effective` single source of truth (`app.api.app`). With
    no active agreements, `compile_rules(base, []) is base`: byte-identical
    to today. A base/agreement conflict (`AgreementConflictError`, §4) is a
    configuration drift that must never take the whole upload pipeline down
    (I3 fail-closed, same philosophy as the boot-time rules-schema fallback
    in `app.api.asgi.create_production_app`): log it and fall back to the
    unmodified base rules with no agreement contract for this request.
    """
    base = store.rules_for(company_id)
    company = store.get_company(company_id) or Company(
        id=company_id, name="", base_currency="USD", is_demo=False,
        created_by=None, created_at="",
    )
    if base is None:
        # T9.8 (D067): unconfigured company -> fail-closed fallback rules
        # (R01 fails with ESCALAR), no agreements compiled in. Never PAGAR.
        return fallback_rules(store.template_rules, company), {}
    # T9.8: the `companies` row is the single source of truth for name/base
    # currency, regardless of whatever was baked into the stored rules
    # document (a shared template, or an older `PUT /rules`). R08 and every
    # explanation must use the company row.
    base = with_company_identity(base, company)
    active = store.list_active_agreements(company_id=company_id)
    if not active:
        return base, {}
    try:
        compiled = compile_rules(base, active)
    except AgreementConflictError as exc:
        _logger.warning(
            "agreement %s conflicts with hand-written rules; using base rules only",
            exc.vendor_key,
        )
        return base, {}
    return compiled.rules, agreement_contract_map(active)


def build_graph_deps(
    settings: Settings,
    rules: RulesConfig,
    ledger: tuple[LedgerEntry, ...],
    *,
    data_root: Path,
    transport: HttpTransport | None = None,
) -> GraphDeps:
    fx_table = load_fx_table(data_root / "data" / "fx.json")
    jev_client = build_decision_client(settings, transport=transport)
    # The JEV label must report the model actually used: the native
    # `jev_model` only when the native backend is in play, otherwise the
    # plan-B role model `graph/folder_batch.py` already resolves the same way.
    jev_label = (
        settings.jev_model
        if resolve_backend(settings) == "jev"
        else model_for_role("jev", settings)
    )
    return GraphDeps(
        extractor=get_llm("extractor", settings, transport=transport),
        verifier=get_llm("verifier", settings, transport=transport),
        jev=jev_client,
        rules=rules,
        fx=fx_table,
        ledger=ledger,
        company_name=rules.company.name,
        rules_version=RULES_VERSION,
        model_extractor=settings.extractor_model,
        model_verifier=settings.verifier_model,
        jev_label=jev_label,
        contracts_dir=data_root / "data" / "contracts",
    )


@dataclass(frozen=True)
class ProductionProcessorConfig:
    store: SqlStore
    settings: Settings
    data_root: Path
    deps_factory: DepsFactory
    checkpointer: BaseCheckpointSaver
    tracer: TraceSession | None
    phase: Literal["demo"] = "demo"
    # One fresh session per upload: a LangSmith session reports its own
    # latest run, so sharing one across concurrent requests could mislabel traces.
    tracer_factory: Callable[[], TraceSession] | None = None


def _trace_session(config: ProductionProcessorConfig) -> TraceSession | None:
    """Best-effort: a tracer that cannot be built never blocks the decision."""
    if config.tracer_factory is None:
        return config.tracer
    try:
        return config.tracer_factory()
    except Exception:
        _logger.warning("tracing unavailable for this upload; continuing without it")
        return NullTrace()


def process_upload(
    config: ProductionProcessorConfig, upload: InvoiceUpload, owner_id: str
) -> DecisionRecord:
    # T9.8 (D067): the company is set by the API around this call.
    company_id = CURRENT_COMPANY.get()
    # T9.1 (D061) §4: the live pipeline decides against the EFFECTIVE rules
    # (base + compiled active confirmed agreements), and a vendor with an
    # active agreement uses its confirmed terms for R06/contract lookup
    # instead of `data/contracts/*.txt`.
    rules, agreement_contracts = effective_rules_and_contracts(
        config.store, company_id=company_id
    )
    # fx.json comes from the configured data root: the module-relative default
    # path does not exist when the package is installed into site-packages.
    # T9.8: expressed in the company's base currency.
    fx_path = config.data_root / "data" / "fx.json"
    fx_table = load_fx_table(fx_path) if fx_path.is_file() else load_fx_table()
    try:
        company_fx = rebase_fx_table(fx_table, rules.company.base_currency)
    except KeyError:
        raise InvoiceRejected("unsupported_base_currency") from None
    rebased = company_fx is not fx_table
    fx_table = company_fx
    prior = settled_ledger_from_store(config.store, fx_table, company_id=company_id)
    ledger_view = ledger_view_for_upload(upload, prior)
    deps = config.deps_factory(config.settings, rules, ledger_view)
    if rebased:
        deps = dataclasses.replace(deps, fx=fx_table)
    if agreement_contracts:
        deps = dataclasses.replace(deps, agreement_contracts=agreement_contracts)
    # P0 safety fix: invoices still ESCALAR (no human decision yet) feed R05
    # duplicate-of-pending only; never merged into `ledger_view` above, so
    # R03/R07/R17/R21 never count an unapproved invoice toward a budget.
    pending_view = pending_ledger_from_store(config.store, fx_table, company_id=company_id)
    if pending_view:
        deps = dataclasses.replace(deps, pending_ledger=pending_view)
    channel: IngestChannel = upload.channel
    try:
        return run_invoice(
            deps,
            raw=upload.content,
            channel=channel,
            invoice_id=upload.invoice_id,
            received_at=upload.received_at,
            checkpointer=config.checkpointer,
            thread_id=upload.invoice_id,
            tracer=_trace_session(config),
            phase=config.phase,
            owner_id=owner_id,
        )
    except GraphError as exc:
        raise InvoiceRejected(exc.code) from exc


def make_production_processor(
    store: SqlStore,
    *,
    settings: Settings | None = None,
    data_root: Path | None = None,
    deps_factory: DepsFactory | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    tracer: TraceSession | None = None,
    tracer_factory: Callable[[], TraceSession] | None = None,
) -> Processor:
    """Factory used by `create_production_app`. Tests may inject `deps_factory`."""
    root = data_root if data_root is not None else repo_root_from_module()
    effective_settings = settings if settings is not None else load_settings()
    saver = checkpointer if checkpointer is not None else _PROCESS_CHECKPOINTER

    def default_factory(
        s: Settings,
        rules: RulesConfig,
        ledger: tuple[LedgerEntry, ...],
    ) -> GraphDeps:
        return build_graph_deps(s, rules, ledger, data_root=root)

    factory = deps_factory if deps_factory is not None else default_factory
    config = ProductionProcessorConfig(
        store=store,
        settings=effective_settings,
        data_root=root,
        deps_factory=factory,
        checkpointer=saver,
        tracer=tracer,
        tracer_factory=tracer_factory,
    )

    def processor(upload: InvoiceUpload, owner_id: str) -> DecisionRecord:
        return process_upload(config, upload, owner_id)

    return processor


__all__ = [
    "ProductionProcessorConfig",
    "build_graph_deps",
    "effective_rules_and_contracts",
    "ledger_view_for_upload",
    "make_production_processor",
    "pending_ledger_from_store",
    "process_upload",
    "settled_ledger_from_store",
]
