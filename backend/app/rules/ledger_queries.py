"""T2.3 — Pure ledger queries over settled entries (used by R03/R05/R07)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from app.rules.context import LedgerEntry
from app.rules.normalize import normalize_beneficiary

DuplicateMatch = Literal["exact", "probable"]
_COUNTED_DECISIONS = frozenset({"PAGAR", "aprobada_humano"})


def _received(dt: str) -> datetime | None:
    try:
        return datetime.fromisoformat(dt.replace("Z", "+00:00"))
    except ValueError:
        return None


def _counted(entries: tuple[LedgerEntry, ...]) -> tuple[LedgerEntry, ...]:
    return tuple(e for e in entries if e.decision in _COUNTED_DECISIONS)


def period_paid_total(entries: tuple[LedgerEntry, ...], year: int, month: int) -> float:
    total = 0.0
    for entry in _counted(entries):
        stamp = _received(entry.received_at)
        if stamp is not None and stamp.year == year and stamp.month == month:
            total += entry.amount_base
    return total


def department_spent(entries: tuple[LedgerEntry, ...], department: str) -> float:
    return sum(e.amount_base for e in _counted(entries) if e.department == department)


def duplicate_match(
    entries: tuple[LedgerEntry, ...],
    beneficiary_norm: str | None,
    invoice_number: str | None,
    amount: float | None,
    currency: str | None,
    received_at: datetime | None,
) -> DuplicateMatch | None:
    """Exact: same normalized beneficiary + same invoice number.

    Probable: same beneficiary + same amount/currency + different number
    within 30 days (by received_at). Only compares against already-processed entries.
    """
    if beneficiary_norm is None or invoice_number is None:
        return None
    probable: DuplicateMatch | None = None
    for entry in entries:
        if normalize_beneficiary(entry.beneficiary) != beneficiary_norm:
            continue
        if entry.invoice_number == invoice_number:
            return "exact"
        if (
            amount is not None
            and currency is not None
            and entry.amount_base == amount
            and entry.currency == currency
            and entry.invoice_number != invoice_number
            and received_at is not None
        ):
            stamp = _received(entry.received_at)
            if stamp is not None and abs((received_at - stamp).days) <= 30:
                probable = "probable"
    return probable
