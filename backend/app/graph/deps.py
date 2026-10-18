"""Injectable dependencies for the invoice graph (T3.7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.models.rules_config import RulesConfig
from app.rules.context import ContractTerms, LedgerEntry
from app.rules.fx import FxTable


@dataclass(frozen=True)
class GraphDeps:
    extractor: object
    verifier: object
    jev: object
    rules: RulesConfig
    fx: FxTable
    ledger: tuple[LedgerEntry, ...]
    company_name: str
    rules_version: str
    model_extractor: str
    model_verifier: str
    jev_label: str
    contracts_dir: Path | None = None
    # T9.1 (D061) §4: vendor_key -> confirmed fixed-amount contract terms from an
    # active agreement. When present for the invoice's vendor, the graph's
    # `contract_lookup` node uses these directly (no LLM) instead of
    # `lookup_contract` over `data/contracts/*.txt`. Empty by default so every
    # existing `GraphDeps(...)` call site (dev motor, folder batch, tests)
    # keeps today's behavior untouched.
    agreement_contracts: dict[str, ContractTerms] = field(default_factory=dict)
    # P0 safety fix: invoices still ESCALAR (no human decision yet), for R05
    # duplicate-of-pending only. Empty by default so every existing
    # `GraphDeps(...)` call site (dev motor, folder batch, tests) keeps
    # today's behavior untouched.
    pending_ledger: tuple[LedgerEntry, ...] = ()
    # Contract file names (``data/contracts/<name>.txt``) a human confirmed
    # outside the frozen text (D015 keeps the marker ``confirmed: false``).
    # Empty by default: only the file marker confirms, as before.
    confirmed_contracts: frozenset[str] = frozenset()
