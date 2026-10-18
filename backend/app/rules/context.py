"""T2.3 — Rule execution context (no LLM, no decide())."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.domain import Extraction, JevSignal
from app.models.metered import MeteredLine
from app.models.rules_config import RulesConfig
from app.rules.fx import FxTable


class LedgerEntry(BaseModel):
    """One settled ledger line. Only PAGAR / aprobada_humano count for R03/R07."""

    model_config = ConfigDict(extra="forbid")

    beneficiary: str
    # T5.13 (D063): None = amount could not be converted to base currency. Never 0.0
    # as a silent default; sums over a None line are INDETERMINADO (fail closed).
    amount_base: float | None
    currency: str
    invoice_number: str
    received_at: str  # ISO-8601
    decision: str
    department: str | None = None
    due_date: str | None = None  # ISO-8601 date; T7.2 (D059), additive


class ContractTerms(BaseModel):
    """Terms used by R06. Extra golden fields (fee_amount_alt, caps, clauses) ignored in v1."""

    model_config = ConfigDict(extra="ignore")

    beneficiary: str | None = None
    fee_amount: float
    fee_currency: str
    cited_clauses: list[str] = Field(default_factory=list)


@dataclass
class RuleContext:
    rules: RulesConfig
    fx_table: FxTable
    extraction: Extraction
    contract_terms: ContractTerms | None = None
    contract_confirmed: bool = False
    jev_signals: list[JevSignal] = field(default_factory=list)
    doc_text: str = ""
    ledger: tuple[LedgerEntry, ...] = ()
    received_at: datetime | None = None
    manual_block: bool = False
    metered_lines: tuple[MeteredLine, ...] = ()
