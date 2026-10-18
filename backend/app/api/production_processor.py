"""Wire HTTP invoice upload to LangGraph (G4). Rules come from the live store."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from app.api.schemas import InvoiceRejected, InvoiceUpload
from app.config import Settings, load_settings
from app.extraction.ingest import IngestChannel
from app.graph.build import GraphError, run_invoice
from app.graph.deps import GraphDeps
from app.graph.folder_batch import RULES_VERSION, repo_root_from_module
from app.graph.tracing import TraceSession
from app.jev.decision_client import build_decision_client
from app.llm import HttpTransport, get_llm
from app.models.domain import DecisionRecord, HumanEvent
from app.models.rules_config import RulesConfig
from app.persistence.sql_store import SqlStore
from app.rules.context import LedgerEntry
from app.rules.fx import FxTable, load_fx_table
from app.rules.ledger import Ledger
from app.rules.settlement import settlement_amount_base

Processor = Callable[[InvoiceUpload, str], DecisionRecord]
DepsFactory = Callable[[Settings, RulesConfig, tuple[LedgerEntry, ...]], GraphDeps]

_PROCESS_CHECKPOINTER = MemorySaver()


def _approval_ledger_line(
    record: DecisionRecord, event: HumanEvent, fx: FxTable
) -> LedgerEntry | None:
    if event.action != "aprobada_humano":
        return None
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


def settled_ledger_from_store(store: SqlStore, fx: FxTable | None = None) -> Ledger:
    """Prior PAGAR lines and human approvals already persisted (T7.4 R20).

    T5.13 (D063): ``amount_base`` is recomputed from amount + currency with the
    fixed FX table; an unconvertible amount is stored as ``None``, never 0.0.
    """
    table = fx if fx is not None else load_fx_table()
    settled = Ledger.empty()
    for record in store.decisions.values():
        settlement = _record_settlement(record, table)
        if settlement is not None:
            settled = settled.record_settlement(settlement, invoice_id=record.invoice_id)
        for index, event in enumerate(record.human_events):
            approval = _approval_ledger_line(record, event, table)
            if approval is not None:
                tie = f"{record.invoice_id}:aprobada:{index}"
                settled = settled.record_settlement(approval, invoice_id=tie)
    return settled


def ledger_view_for_upload(upload: InvoiceUpload, prior: Ledger) -> tuple[LedgerEntry, ...]:
    """Every persisted settlement, regardless of the client-supplied ``received_at``.

    T5.13 (D063): everything in the store was already processed in real time, so
    the whole history is "before" this upload. Filtering by the client's date let
    a backdated resubmission hide the original payment from R05.
    """
    del upload  # the view no longer depends on the (untrusted) client date
    return prior.as_tuple()


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
        jev_label=settings.jev_model,
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


def process_upload(
    config: ProductionProcessorConfig, upload: InvoiceUpload, owner_id: str
) -> DecisionRecord:
    # fx.json comes from the configured data root: the module-relative default
    # path does not exist when the package is installed into site-packages.
    fx_path = config.data_root / "data" / "fx.json"
    fx_table = load_fx_table(fx_path) if fx_path.is_file() else load_fx_table()
    prior = settled_ledger_from_store(config.store, fx_table)
    ledger_view = ledger_view_for_upload(upload, prior)
    rules = config.store.rules
    deps = config.deps_factory(config.settings, rules, ledger_view)
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
            tracer=config.tracer,
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
    )

    def processor(upload: InvoiceUpload, owner_id: str) -> DecisionRecord:
        return process_upload(config, upload, owner_id)

    return processor


__all__ = [
    "ProductionProcessorConfig",
    "build_graph_deps",
    "ledger_view_for_upload",
    "make_production_processor",
    "process_upload",
    "settled_ledger_from_store",
]
