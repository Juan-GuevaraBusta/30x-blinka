"""Injectable dependencies for the invoice graph (T3.7)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.models.rules_config import RulesConfig
from app.rules.context import LedgerEntry
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
