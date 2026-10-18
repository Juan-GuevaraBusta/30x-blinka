"""Batch invoice folder runner for CLI (T3.9). Orchestrates run_invoice only."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from app.config import Settings
from app.extraction.ingest import IngestChannel
from app.graph.build import run_invoice
from app.graph.deps import GraphDeps
from app.graph.tracing import TraceSession
from app.jev.decision_client import build_decision_client
from app.llm import HttpTransport, get_llm
from app.models.domain import DecisionRecord
from app.models.rules_config import load_rules_config
from app.motor.golden_runner import enrich_ledger_seed
from app.rules.context import LedgerEntry
from app.rules.fx import load_fx_table
from app.rules.ledger import Ledger, ledger_view_for_invoice, sort_key

RULES_VERSION = "v1"
Phase = Literal["dev", "eval", "demo"]
DepsFactory = Callable[[Settings, tuple[LedgerEntry, ...]], GraphDeps]


class FolderBatchError(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(code if not detail else f"{code}:{detail}")


@dataclass(frozen=True)
class FolderRunReport:
    processed: int
    output_path: Path


def repo_root_from_module() -> Path:
    return Path(__file__).resolve().parents[3]


def load_catalog(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def select_catalog_rows(
    catalog: list[dict],
    invoices_dir: Path,
    repo_root: Path,
) -> list[dict]:
    resolved_dir = invoices_dir.resolve()
    by_name: dict[str, dict] = {}
    for entry in catalog:
        file_path = (repo_root / entry["path"]).resolve()
        if file_path.parent != resolved_dir or not file_path.is_file():
            continue
        by_name[file_path.name] = entry

    rows: list[dict] = []
    for child in sorted(resolved_dir.iterdir(), key=lambda p: p.name):
        if not child.is_file() or child.name.startswith("."):
            continue
        entry = by_name.get(child.name)
        if entry is None:
            raise FolderBatchError("unknown_invoice_file", child.name)
        rows.append(entry)
    rows.sort(key=lambda row: sort_key(row["received_at"], row["id"]))
    return rows


def build_runtime_graph_deps(
    settings: Settings,
    ledger: tuple[LedgerEntry, ...],
    *,
    data_root: Path,
    transport: HttpTransport | None = None,
) -> GraphDeps:
    rules = load_rules_config(data_root / "data" / "rules.json")
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


def _catalog_row_for_ledger(entry: dict) -> dict:
    row = dict(entry)
    if row.get("ledger_seed") and "extraction" in row:
        row["ledger_seed"] = enrich_ledger_seed(row)
    return row


def _record_settlement(record: DecisionRecord, received_at: str) -> LedgerEntry | None:
    if record.decision != "PAGAR":
        return None
    ext = record.extracted
    return LedgerEntry(
        beneficiary=ext.beneficiary or "",
        amount_base=float(ext.amount_base or 0.0),
        currency=ext.currency or "USD",
        invoice_number=ext.invoice_number or "",
        received_at=received_at,
        decision="PAGAR",
        department=ext.department,
        due_date=ext.due_date.isoformat() if ext.due_date else None,
    )


def run_invoice_folder(
    invoices_dir: Path,
    output_path: Path,
    *,
    repo_root: Path | None = None,
    catalog_path: Path | None = None,
    phase: Phase = "dev",
    settings: Settings | None = None,
    deps_factory: DepsFactory | None = None,
    tracer: TraceSession | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> FolderRunReport:
    root = repo_root or repo_root_from_module()
    catalog_file = catalog_path or (root / "data" / "invoices" / "catalog.json")
    effective_settings = settings or Settings()
    factory = deps_factory or (
        lambda s, ledger: build_runtime_graph_deps(
            s, ledger, data_root=root
        )
    )
    saver = checkpointer or MemorySaver()

    catalog = load_catalog(catalog_file)
    rows = select_catalog_rows(catalog, invoices_dir, root)
    settled = Ledger.empty()
    records: list[DecisionRecord] = []

    for entry in rows:
        ledger_row = _catalog_row_for_ledger(entry)
        ledger_view = ledger_view_for_invoice(ledger_row, settled)
        deps = factory(effective_settings, ledger_view)
        file_path = (root / entry["path"]).resolve()
        raw = file_path.read_bytes()
        channel: IngestChannel = entry["channel"]
        received = datetime.fromisoformat(entry["received_at"].replace("Z", "+00:00"))
        invoice_id = entry["id"]
        record = run_invoice(
            deps,
            raw=raw,
            channel=channel,
            invoice_id=invoice_id,
            received_at=received,
            checkpointer=saver,
            thread_id=invoice_id,
            tracer=tracer,
            phase=phase,
        )
        records.append(record)
        settlement = _record_settlement(record, entry["received_at"])
        if settlement is not None:
            settled = settled.record_settlement(settlement, invoice_id=invoice_id)

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        "phase": phase,
        "invoices_dir": str(invoices_dir.resolve()),
        "records": [r.model_dump(mode="json") for r in records],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    output_path.write_text(text, encoding="utf-8")
    return FolderRunReport(processed=len(records), output_path=output_path)


__all__ = [
    "FolderBatchError",
    "FolderRunReport",
    "RULES_VERSION",
    "build_runtime_graph_deps",
    "load_catalog",
    "repo_root_from_module",
    "run_invoice_folder",
    "select_catalog_rows",
]
