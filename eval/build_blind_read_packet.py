#!/usr/bin/env python3
"""T5.4 — build the blind-read packet (docs/T5_4_SPEC.md §7).

Exports five cards into eval/reports/blind_read_packet/ using the G2 golden
motor: true extraction from data/golden/<split>.json, JEV signals already
injected into the RuleContext, and the plain
run_deterministic_checks / decide path. This is the exact walk
`app.motor.golden_runner.run_golden_split` does (same `sort_key` order,
`build_rule_context`, `ledger_view_for_invoice`, settlements recorded only
when the decision is PAGAR) -- it is NOT the G3 end-to-end graph: no
`run_invoice`, no LangGraph, no `/tmp/g3_e2e_decisions.json`. No LLM call,
no network.

Card content is exactly `RecordContext.from_rule_context`, then
`build_summary`, `enrich_check_details` (rule/name/result/detail per check)
and `build_next_step` -- copied verbatim from
`backend/app/records/build.py`. No `expected_decision`, no `expected_rules`,
no `case`, no `reason`, no raw `DecisionRecord`, no code paths
(docs/T5_4_SPEC.md §5, §7 step 5, invariants I2/I5).

Split is fixed to "dev"; passing --split holdout aborts before touching any
file (docs/T5_4_SPEC.md §7 step 1, §0: "No abrir ... holdout.json").
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from app.models.rules_config import load_rules_config
from app.motor import golden_runner as gr
from app.records.build import (
    RecordContext,
    build_next_step,
    build_summary,
    enrich_check_details,
)
from app.rules.context import LedgerEntry
from app.rules.decide import decide
from app.rules.fx import load_fx_table
from app.rules.ledger import Ledger, ledger_view_for_invoice, sort_key
from app.rules.run_checks import run_deterministic_checks

# Order from docs/T5_4_SPEC.md §7 (the `case` column there is only for the
# person assembling the packet -- it is never copied into a card or into
# eval/reports/blind_read.md).
TARGET_IDS: tuple[str, ...] = ("dev-001", "dev-013", "dev-015", "dev-018", "dev-021")

PACKET_DIR = "blind_read_packet"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _looks_unfilled(text: str) -> bool:
    """Guard against an unrendered template (stray `{..}`), an exception
    trace, or an empty string reaching a card (docs/T5_4_SPEC.md §7 step 7:
    escalate to Rules Engine, never improvise a sentence)."""
    stripped = text.strip()
    if not stripped:
        return True
    if "{" in stripped and "}" in stripped:
        return True
    return "Traceback (most recent call last)" in stripped


def _escape_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _render_card(invoice_id: str, summary: str, checks, next_step: str) -> str:
    lines = [f"# Ficha {invoice_id}", "", "## Resumen", "", summary, "", "## Chequeos", ""]
    lines.append("| Regla | Nombre | Resultado | Detalle |")
    lines.append("|---|---|---|---|")
    for check in checks:
        lines.append(
            f"| {check.rule} | {_escape_cell(check.name)} | {check.result} "
            f"| {_escape_cell(check.detail)} |"
        )
    lines.extend(["", "## Siguiente paso", "", next_step, ""])
    return "\n".join(lines)


def build_packet(split: str, repo_root: Path) -> dict[str, dict]:
    if split != "dev":
        raise SystemExit(
            f"T5.4 solo arma fichas del split 'dev' (docs/T5_4_SPEC.md §7 step 1); "
            f"se pidió '{split}'. Abortando sin tocar data/golden/holdout.json."
        )

    rules = load_rules_config(repo_root / "data" / "rules.json")
    fx_table = load_fx_table(repo_root / "data" / "fx.json")
    notes = gr._catalog_notes(repo_root)
    entries = sorted(
        gr._load_golden(repo_root, split),
        key=lambda e: sort_key(e["received_at"], e["invoice_id"]),
    )

    settled = Ledger.empty()
    cards: dict[str, dict] = {}
    remaining = set(TARGET_IDS)

    for entry in entries:
        row = dict(entry)
        row["id"] = entry["invoice_id"]
        row["ledger_seed"] = gr.enrich_ledger_seed(entry)
        ledger_view = ledger_view_for_invoice(row, settled)
        ctx = gr.build_rule_context(
            entry, rules=rules, fx_table=fx_table, ledger=ledger_view, catalog_notes=notes
        )
        checks = run_deterministic_checks(ctx)
        proposed = decide(checks)

        invoice_id = entry["invoice_id"]
        if invoice_id in remaining:
            record_ctx = RecordContext.from_rule_context(ctx, invoice_id=invoice_id)
            enriched = enrich_check_details(checks, record_ctx)
            summary = build_summary(proposed, checks, record_ctx)
            next_step = build_next_step(proposed, checks, record_ctx)

            for text in (summary, next_step, *(c.detail for c in enriched)):
                if _looks_unfilled(text):
                    raise SystemExit(
                        f"Ficha {invoice_id} salió ilegible (placeholder sin rellenar, "
                        "texto vacío o traza de excepción). Se escala a Rules Engine; "
                        "T5.4 sigue PENDIENTE. No se parchea la plantilla aquí."
                    )
            cards[invoice_id] = {"summary": summary, "checks": enriched, "next_step": next_step}
            remaining.discard(invoice_id)

        if proposed == "PAGAR":
            ext = ctx.extraction
            settlement = LedgerEntry(
                beneficiary=ext.beneficiary or "",
                amount_base=float(ext.amount_base or 0.0),
                currency=ext.currency or "USD",
                invoice_number=ext.invoice_number or "",
                received_at=entry["received_at"],
                decision="PAGAR",
                department=ext.department,
            )
            settled = settled.record_settlement(settlement, invoice_id=invoice_id)

    if remaining:
        raise SystemExit(
            f"Ids no encontrados en el split '{split}': {sorted(remaining)}. "
            "Revisar data/invoices/catalog.json / data/golden/dev.json."
        )

    # docs/T5_4_SPEC.md §7 step 6: two cards with the same `summary` are not
    # allowed to both ship; this only detects it and stops -- substituting
    # the later id for another dev-* card is a judgment call for whoever
    # runs this script, not something to automate silently.
    seen_summaries: dict[str, str] = {}
    for invoice_id in TARGET_IDS:
        summary = cards[invoice_id]["summary"]
        if summary in seen_summaries:
            raise SystemExit(
                f"{invoice_id} y {seen_summaries[summary]} comparten el mismo summary. "
                "docs/T5_4_SPEC.md §7 step 6: sustituir el id posterior por otro dev-* "
                "del mismo split con resumen distinto y anotar el cambio en el reporte "
                "(no se busca variedad en el holdout)."
            )
        seen_summaries[summary] = invoice_id

    return cards


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the T5.4 blind-read packet from the G2 golden motor."
    )
    parser.add_argument("--split", default="dev", help="Golden split (must stay 'dev').")
    args = parser.parse_args(argv)

    repo_root = _repo_root()
    cards = build_packet(args.split, repo_root)

    out_dir = repo_root / "eval" / "reports" / PACKET_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    command = "python " + " ".join(["eval/build_blind_read_packet.py", *(argv or sys.argv[1:])])
    print(f"command: {command}")
    for invoice_id in TARGET_IDS:
        card = cards[invoice_id]
        text = _render_card(invoice_id, card["summary"], card["checks"], card["next_step"])
        path = out_dir / f"{invoice_id}.md"
        path.write_text(text, encoding="utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"{digest}  eval/reports/{PACKET_DIR}/{invoice_id}.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
