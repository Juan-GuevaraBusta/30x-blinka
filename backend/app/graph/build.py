"""LangGraph invoice pipeline: wire-only orchestration (T3.7)."""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.extraction.contracts import ContractLookupError, lookup_contract
from app.extraction.extract import ExtractError, extract_document
from app.extraction.ingest import IngestChannel, IngestError, ingest_bytes
from app.extraction.metered import extract_metered_lines
from app.gate.final_gate import GateInput, run_final_gate
from app.graph.deps import GraphDeps
from app.graph.state import InvoiceState
from app.graph.tracing import NullTrace, TraceSession
from app.jev.run import JevRunError, ask_invoice_signals, build_jev_state
from app.models.domain import (
    SEVERITY,
    CheckResult,
    Decision,
    DecisionRecord,
    Extraction,
    JevSignal,
    ModelVersions,
    TraceRef,
    VerifierReport,
)
from app.models.metered import MeteredLine
from app.records.build import (
    RecordContext,
    build_admin_notice,
    build_next_step,
    build_summary,
    build_technical_error_summary,
    enrich_check_details,
)
from app.rules.context import ContractTerms, RuleContext
from app.rules.decide import decide
from app.rules.normalize import normalize_beneficiary
from app.rules.run_checks import run_deterministic_checks
from app.rules.settlement import with_base_amount
from app.rules.variable_pricing import find_pricing_terms
from app.verifier.run import VerifierError, verify_decision


class GraphError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _tech_escalate() -> Command:
    return Command(goto="escalate_technical", update={"errors": ["error_tecnico"]})


def _parse_received_at(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def _rule_context(deps: GraphDeps, state: InvoiceState) -> RuleContext:
    extraction = Extraction.model_validate(state["extraction"])
    terms_raw = state.get("contract_terms")
    terms = ContractTerms.model_validate(terms_raw) if terms_raw else None
    jev = [JevSignal.model_validate(item) for item in state.get("jev_signals", [])]
    metered_raw = state.get("metered_lines") or []
    metered = tuple(MeteredLine.model_validate(item) for item in metered_raw)
    return RuleContext(
        rules=deps.rules,
        fx_table=deps.fx,
        extraction=extraction,
        contract_terms=terms,
        contract_confirmed=bool(state.get("contract_confirmed")),
        jev_signals=jev,
        doc_text=state.get("doc_text", ""),
        ledger=deps.ledger,
        pending_ledger=deps.pending_ledger,
        received_at=_parse_received_at(state["received_at"]),
        manual_block=False,
        metered_lines=metered,
    )


def _checks_from_state(state: InvoiceState) -> list[CheckResult]:
    return [CheckResult.model_validate(item) for item in state.get("check_results", [])]


def _build_escalate_record(deps: GraphDeps, state: InvoiceState) -> dict:
    errors = state.get("errors") or []
    if "documento ilegible" in errors:
        default_summary = build_technical_error_summary("documento ilegible")
    else:
        default_summary = build_technical_error_summary("error_tecnico")

    summary = state.get("summary")
    admin_notice = state.get("admin_notice")
    preserve_frenar = (
        state.get("proposed_decision") == "FRENAR"
        and summary is not None
        and bool(summary.strip())
        and admin_notice is not None
        and bool(admin_notice.strip())
    )

    if preserve_frenar:
        final_decision: Decision = "FRENAR"
        final_summary = summary
        final_admin = admin_notice
        final_next = state.get("next_step") or "Requiere revisión humana."
    else:
        final_decision = "ESCALAR"
        final_summary = default_summary
        final_admin = None
        final_next = "Requiere revisión humana."

    extraction = (
        Extraction.model_validate(state["extraction"])
        if "extraction" in state
        else Extraction()
    )
    checks = _checks_from_state(state) if "check_results" in state else []
    jev_signals = (
        [JevSignal.model_validate(item) for item in state["jev_signals"]]
        if "jev_signals" in state
        else []
    )
    if "verifier_report" in state:
        verifier = VerifierReport.model_validate(state["verifier_report"])
    else:
        verifier = VerifierReport(consistent=False, issues=[])

    record = DecisionRecord(
        id=state["invoice_id"],
        invoice_id=state["invoice_id"],
        received_at=_parse_received_at(state["received_at"]),
        decision=final_decision,
        severity=SEVERITY[final_decision],
        summary=final_summary,
        extracted=extraction,
        checks=checks,
        jev_signals=jev_signals,
        verifier=verifier,
        admin_notice=final_admin,
        next_step=final_next,
        trace=TraceRef(),
        versions=ModelVersions(
            rules_version=deps.rules_version,
            model_extractor=deps.model_extractor,
            model_verifier=deps.model_verifier,
            jev=deps.jev_label,
        ),
        human_events=[],
    )
    return record.model_dump(mode="json")


def _make_nodes(deps: GraphDeps):
    def ingest(state: InvoiceState) -> Command[Literal["extract", "escalate_technical"]]:
        try:
            raw = base64.b64decode(state["raw_b64"])
            channel = state["channel"]
            result = ingest_bytes(raw, channel=channel)  # type: ignore[arg-type]
            return Command(goto="extract", update={"doc_text": result.text})
        except IngestError as exc:
            if exc.code in ("illegible", "empty_text"):
                return Command(
                    goto="escalate_technical",
                    update={"errors": ["documento ilegible"]},
                )
            return Command(goto="escalate_technical", update={"errors": ["error_tecnico"]})
        except Exception:
            return _tech_escalate()

    def extract(state: InvoiceState) -> Command[Literal["contract_lookup", "escalate_technical"]]:
        try:
            # T5.13 (D063): amount_base/fx come from the fixed FX table, once, here --
            # never from the extractor -- and are persisted in the record's extraction.
            extraction = with_base_amount(
                extract_document(state["doc_text"], deps.extractor), deps.fx
            )
            update: dict = {"extraction": extraction.model_dump(mode="json")}
            pricing = find_pricing_terms(deps.rules, extraction.beneficiary)
            if pricing is not None:
                metered = extract_metered_lines(state["doc_text"], deps.extractor)
                update["metered_lines"] = [line.model_dump(mode="json") for line in metered]
            return Command(goto="contract_lookup", update=update)
        except (ExtractError, Exception):
            return _tech_escalate()

    def contract_lookup(
        state: InvoiceState,
    ) -> Command[Literal["jev_checks", "escalate_technical"]]:
        try:
            extraction = Extraction.model_validate(state["extraction"])
            # T9.1 (D061) §4: a vendor with an active, confirmed fixed-amount
            # agreement uses its terms directly -- no LLM call -- instead of
            # `lookup_contract` over `data/contracts/*.txt`.
            vendor_key = normalize_beneficiary(extraction.beneficiary)
            agreement_terms = (
                deps.agreement_contracts.get(vendor_key) if vendor_key is not None else None
            )
            if agreement_terms is not None:
                cited = agreement_terms.clause_text or (
                    agreement_terms.cited_clauses[0] if agreement_terms.cited_clauses else None
                )
                return Command(
                    goto="jev_checks",
                    update={
                        "contract_terms": agreement_terms.model_dump(mode="json"),
                        "contract_confirmed": True,
                        "cited_clause": cited,
                    },
                )
            record = lookup_contract(
                extraction.beneficiary,
                deps.extractor,
                contracts_dir=deps.contracts_dir,
            )
        except ContractLookupError:
            return _tech_escalate()
        except Exception:
            return _tech_escalate()

        if not record.found or record.terms is None or not record.confirmed:
            return Command(
                goto="jev_checks",
                update={
                    "contract_terms": None,
                    "contract_confirmed": False,
                    "cited_clause": None,
                },
            )

        cited = record.cited_clauses[0] if record.cited_clauses else None
        return Command(
            goto="jev_checks",
            update={
                "contract_terms": record.terms.model_dump(mode="json"),
                "contract_confirmed": True,
                "cited_clause": cited,
            },
        )

    def jev_checks(state: InvoiceState) -> Command[Literal["det_checks", "escalate_technical"]]:
        try:
            extraction = Extraction.model_validate(state["extraction"])
            jev_state = build_jev_state(
                extraction=extraction,
                company_name=deps.company_name,
                doc_text=state["doc_text"],
                cited_clause=state.get("cited_clause"),
            )
            signals = ask_invoice_signals(deps.jev, jev_state)
            return Command(
                goto="det_checks",
                update={"jev_signals": [s.model_dump(mode="json") for s in signals]},
            )
        except (JevRunError, Exception):
            return _tech_escalate()

    def det_checks(state: InvoiceState) -> Command[Literal["aggregate", "escalate_technical"]]:
        try:
            ctx = _rule_context(deps, state)
            checks = run_deterministic_checks(ctx)
            return Command(
                goto="aggregate",
                update={
                    "check_results": [c.model_dump(mode="json") for c in checks],
                    "extraction": ctx.extraction.model_dump(mode="json"),
                },
            )
        except Exception:
            return _tech_escalate()

    def aggregate(state: InvoiceState) -> Command[Literal["record", "escalate_technical"]]:
        try:
            checks = _checks_from_state(state)
            proposed = decide(checks)
            return Command(goto="record", update={"proposed_decision": proposed})
        except Exception:
            return _tech_escalate()

    def record(state: InvoiceState) -> Command[Literal["verify", "escalate_technical"]]:
        try:
            ctx = _rule_context(deps, state)
            checks = _checks_from_state(state)
            proposed = state["proposed_decision"]
            record_ctx = RecordContext.from_rule_context(ctx, invoice_id=state["invoice_id"])
            enriched = enrich_check_details(checks, record_ctx)
            summary = build_summary(proposed, checks, record_ctx)
            admin_notice = build_admin_notice(proposed, checks, record_ctx, summary)
            next_step = build_next_step(proposed, checks, record_ctx)
            return Command(
                goto="verify",
                update={
                    "check_results": [c.model_dump(mode="json") for c in enriched],
                    "summary": summary,
                    "admin_notice": admin_notice,
                    "next_step": next_step,
                },
            )
        except Exception:
            return _tech_escalate()

    def verify(state: InvoiceState) -> Command[Literal["final_gate", "escalate_technical"]]:
        try:
            ctx = _rule_context(deps, state)
            checks = _checks_from_state(state)
            extraction = ctx.extraction
            proposed = state["proposed_decision"]
            outcome = verify_decision(
                deps.verifier,
                doc_text=state["doc_text"],
                extraction=extraction,
                checks=checks,
                proposed=proposed,
                jev_signals=ctx.jev_signals,
                rules_version=deps.rules_version,
                invoice_id=state["invoice_id"],
                beneficiary=extraction.beneficiary,
            )
            summary = state["summary"]
            if outcome.summary is not None:
                summary = f"{summary} {outcome.summary}"
            admin_notice = state.get("admin_notice")
            if outcome.admin_notice is not None:
                admin_notice = outcome.admin_notice
            return Command(
                goto="final_gate",
                update={
                    "verifier_report": outcome.report.model_dump(mode="json"),
                    "elevated_decision": outcome.decision,
                    "summary": summary,
                    "admin_notice": admin_notice,
                },
            )
        except (VerifierError, Exception):
            return _tech_escalate()

    def final_gate(state: InvoiceState) -> Command[Literal["__end__"]]:
        try:
            ctx = _rule_context(deps, state)
            checks = _checks_from_state(state)
            extraction = ctx.extraction
            jev_signals = ctx.jev_signals
            verifier = VerifierReport.model_validate(state["verifier_report"])
            elevated = state["elevated_decision"]
            proposed = state["proposed_decision"]

            draft = DecisionRecord(
                id=state["invoice_id"],
                invoice_id=state["invoice_id"],
                received_at=_parse_received_at(state["received_at"]),
                decision=elevated,
                severity=SEVERITY[elevated],
                summary=state["summary"],
                extracted=extraction,
                checks=checks,
                jev_signals=jev_signals,
                verifier=verifier,
                admin_notice=state.get("admin_notice"),
                next_step=state["next_step"],
                trace=TraceRef(),
                versions=ModelVersions(
                    rules_version=deps.rules_version,
                    model_extractor=deps.model_extractor,
                    model_verifier=deps.model_verifier,
                    jev=deps.jev_label,
                ),
                human_events=[],
            )
            gate_inp = GateInput(
                proposed_decision=proposed,
                record=draft,
                jev_thresholds=deps.rules.jev_thresholds,
            )
            out = run_final_gate(gate_inp)
            return Command(
                goto=END,
                update={
                    "record": out.record.model_dump(mode="json"),
                    "final_decision": out.final_decision,
                },
            )
        except Exception:
            record_dump = _build_escalate_record(deps, state)
            parsed = DecisionRecord.model_validate(record_dump)
            return Command(
                goto=END,
                update={
                    "record": record_dump,
                    "final_decision": parsed.decision,
                    "errors": ["error_tecnico"],
                },
            )

    def escalate_technical(state: InvoiceState) -> Command[Literal["__end__"]]:
        try:
            record_dump = _build_escalate_record(deps, state)
            parsed = DecisionRecord.model_validate(record_dump)
            return Command(
                goto=END,
                update={
                    "record": record_dump,
                    "final_decision": parsed.decision,
                },
            )
        except Exception:
            minimal = DecisionRecord(
                id=state.get("invoice_id") or "unknown",
                invoice_id=state.get("invoice_id") or "unknown",
                received_at=_parse_received_at(
                    state.get("received_at") or datetime.now().astimezone().isoformat()
                ),
                decision="ESCALAR",
                severity=1,
                summary=build_technical_error_summary("error_tecnico"),
                extracted=Extraction(),
                checks=[],
                jev_signals=[],
                verifier=VerifierReport(consistent=False, issues=[]),
                admin_notice=None,
                next_step="Requiere revisión humana.",
                trace=TraceRef(),
                versions=ModelVersions(
                    rules_version=deps.rules_version,
                    model_extractor=deps.model_extractor,
                    model_verifier=deps.model_verifier,
                    jev=deps.jev_label,
                ),
                human_events=[],
            )
            return Command(
                goto=END,
                update={
                    "record": minimal.model_dump(mode="json"),
                    "final_decision": "ESCALAR",
                },
            )

    return {
        "ingest": ingest,
        "extract": extract,
        "contract_lookup": contract_lookup,
        "jev_checks": jev_checks,
        "det_checks": det_checks,
        "aggregate": aggregate,
        "record": record,
        "verify": verify,
        "final_gate": final_gate,
        "escalate_technical": escalate_technical,
    }


def compile_invoice_graph(deps: GraphDeps, checkpointer: BaseCheckpointSaver):
    nodes = _make_nodes(deps)
    builder = StateGraph(InvoiceState)
    for name, fn in nodes.items():
        builder.add_node(name, fn)
    builder.add_edge(START, "ingest")
    return builder.compile(checkpointer=checkpointer)


def _record_writer(graph: object, config: dict) -> str:
    history = list(graph.get_state_history(config))  # type: ignore[attr-defined]
    if len(history) >= 2 and history[1].next:
        node = history[1].next[0]
        if node in ("final_gate", "escalate_technical"):
            return node
    return "final_gate"


def run_invoice(
    deps: GraphDeps,
    *,
    raw: bytes,
    channel: IngestChannel,
    invoice_id: str,
    received_at: datetime,
    checkpointer: BaseCheckpointSaver,
    thread_id: str,
    tracer: TraceSession | None = None,
    phase: Literal["dev", "eval", "demo"] = "dev",
    owner_id: str | None = None,
) -> DecisionRecord:
    if not invoice_id or not invoice_id.strip():
        raise GraphError("empty_invoice_id")
    if received_at.tzinfo is None:
        raise GraphError("naive_datetime")

    session: TraceSession = tracer if tracer is not None else NullTrace()
    metadata = {
        "invoice_id": invoice_id,
        "rules_version": deps.rules_version,
        "model_extractor": deps.model_extractor,
        "model_verifier": deps.model_verifier,
        "jev": deps.jev_label,
        "phase": phase,
    }
    tags = ["invoice", phase]
    if owner_id is not None:
        trimmed = owner_id.strip()
        if trimmed:
            metadata["owner_id"] = owner_id
            tags.append(owner_id)
    initial: InvoiceState = {
        "raw_b64": base64.b64encode(raw).decode("ascii"),
        "channel": channel,
        "invoice_id": invoice_id,
        "received_at": received_at.isoformat(),
    }
    graph = compile_invoice_graph(deps, checkpointer)
    config = {
        "configurable": {"thread_id": thread_id},
        **session.open_config(metadata=metadata, tags=tags),
    }
    final_state = graph.invoke(initial, config)
    record = DecisionRecord.model_validate(final_state["record"])
    try:
        finished = session.finish(record.decision)
        if finished is None:
            return record
        patched = record.model_copy(update={"trace": finished})
        checkpoint_config = {"configurable": {"thread_id": thread_id}}
        graph.update_state(
            checkpoint_config,
            {"record": patched.model_dump(mode="json")},
            as_node=_record_writer(graph, checkpoint_config),
        )
    except Exception:
        return record
    return patched


__all__ = [
    "GraphError",
    "compile_invoice_graph",
    "run_invoice",
]
