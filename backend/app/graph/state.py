"""LangGraph shared state for invoice processing (T3.7)."""

from __future__ import annotations

import operator
from typing import Annotated

from typing_extensions import TypedDict

from app.models.domain import Decision


class InvoiceState(TypedDict, total=False):
    raw_b64: str
    channel: str
    invoice_id: str
    received_at: str
    doc_text: str
    extraction: dict
    contract_terms: dict | None
    contract_confirmed: bool
    cited_clause: str | None
    jev_signals: list[dict]
    metered_lines: list[dict]
    check_results: list[dict]
    proposed_decision: Decision
    elevated_decision: Decision
    summary: str
    admin_notice: str | None
    next_step: str
    verifier_report: dict
    record: dict
    final_decision: Decision
    errors: Annotated[list[str], operator.add]
