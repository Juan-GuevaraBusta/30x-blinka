"""T2.4 — Deterministic ledger: ordered settlements for R03/R05/R07 context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.rules.context import LedgerEntry
from app.rules.ledger_queries import COUNTED_DECISIONS


def _aware_utc(received_at: datetime | str) -> datetime:
    if isinstance(received_at, str):
        parsed = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
    else:
        parsed = received_at
    if parsed.tzinfo is None:
        raise ValueError("received_at must be timezone-aware")
    return parsed.astimezone(UTC)


def sort_key(received_at: datetime | str, tie_id: str) -> tuple[str, str]:
    """Lexicographic order key: canonical UTC ISO timestamp, then tie_id (invoice_id)."""
    stamp = _aware_utc(received_at)
    canonical = stamp.isoformat().replace("+00:00", "Z")
    return (canonical, tie_id)


def _line_key(tie_id: str, entry: LedgerEntry) -> tuple[str, str]:
    return sort_key(entry.received_at, tie_id)


@dataclass(frozen=True, slots=True)
class Ledger:
    """Immutable ordered ledger lines. Only counted decisions are stored."""

    _lines: tuple[tuple[str, LedgerEntry], ...] = ()

    @staticmethod
    def empty() -> Ledger:
        return Ledger()

    @staticmethod
    def from_seed(rows: list[dict]) -> Ledger:
        """Build ledger from catalog/golden ``ledger_seed`` (counted lines only)."""
        lines: list[tuple[str, LedgerEntry]] = []
        for row in rows:
            decision = row["decision"]
            if decision not in COUNTED_DECISIONS:
                continue
            entry = LedgerEntry(
                beneficiary=row["beneficiary"],
                amount_base=float(row["amount_base"]),
                currency=row["currency"],
                invoice_number=row["invoice_number"],
                received_at=row["received_at"],
                decision=decision,
                department=row.get("department"),
            )
            tie_id = row.get("invoice_id") or row["invoice_number"]
            lines.append((tie_id, entry))
        ordered = tuple(sorted(lines, key=lambda pair: _line_key(pair[0], pair[1])))
        return Ledger(_lines=ordered)

    def record_settlement(self, entry: LedgerEntry, *, invoice_id: str) -> Ledger:
        """Append a settlement line when decision counts; otherwise return self."""
        if entry.decision not in COUNTED_DECISIONS:
            return self
        combined = (*self._lines, (invoice_id, entry))
        new_lines = tuple(sorted(combined, key=lambda p: _line_key(p[0], p[1])))
        return Ledger(_lines=new_lines)

    def entries_before(self, received_at: datetime, invoice_id: str) -> tuple[LedgerEntry, ...]:
        """Entries strictly before ``(received_at, invoice_id)`` in global process order."""
        cutoff = sort_key(received_at, invoice_id)
        return tuple(entry for tie_id, entry in self._lines if _line_key(tie_id, entry) < cutoff)

    def as_tuple(self) -> tuple[LedgerEntry, ...]:
        return tuple(entry for _, entry in self._lines)


def ledger_view_for_invoice(catalog_row: dict, prior_settled: Ledger) -> tuple[LedgerEntry, ...]:
    """Ledger snapshot for rule checks before deciding this invoice (T2.8 runner).

    Seed rows are synthetic prior settlements and are included whole. Only
    ``prior_settled`` lines from the ordered run are filtered with ``entries_before``.
    """
    seed = Ledger.from_seed(catalog_row.get("ledger_seed", []))
    received = _aware_utc(catalog_row["received_at"])
    invoice_id = catalog_row["id"]
    prior = prior_settled.entries_before(received, invoice_id)
    return seed.as_tuple() + prior
