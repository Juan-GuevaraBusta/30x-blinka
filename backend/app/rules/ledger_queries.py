"""T2.3 — Pure ledger queries over settled entries (used by R03/R05/R07/R21).

T5.13 (D063): a line whose ``amount_base`` is ``None`` (amount not convertible)
makes every sum that would include it return ``None`` -- callers turn that into
INDETERMINADO, never into a 0.0 contribution.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Literal

from app.rules.context import LedgerEntry
from app.rules.normalize import normalize_beneficiary, normalize_invoice_number

DuplicateMatch = Literal["exact", "probable"]
COUNTED_DECISIONS = frozenset({"PAGAR", "aprobada_humano"})
_COUNTED_DECISIONS = COUNTED_DECISIONS


def _received(dt: str) -> datetime | None:
    try:
        return datetime.fromisoformat(dt.replace("Z", "+00:00"))
    except ValueError:
        return None


def _counted(entries: tuple[LedgerEntry, ...]) -> tuple[LedgerEntry, ...]:
    return tuple(e for e in entries if e.decision in _COUNTED_DECISIONS)


def _sum_known(entries: Iterable[LedgerEntry]) -> float | None:
    total = 0.0
    for entry in entries:
        if entry.amount_base is None:
            return None
        total += entry.amount_base
    return total


def period_paid_total(entries: tuple[LedgerEntry, ...], year: int, month: int) -> float | None:
    in_period = []
    for entry in _counted(entries):
        stamp = _received(entry.received_at)
        if stamp is not None and stamp.year == year and stamp.month == month:
            in_period.append(entry)
    return _sum_known(in_period)


def department_spent(entries: tuple[LedgerEntry, ...], department: str) -> float | None:
    return _sum_known(e for e in _counted(entries) if e.department == department)


def department_spent_for_budget(
    entries: tuple[LedgerEntry, ...],
    department: str,
    received_at: datetime | None,
) -> float | None:
    """R07 spend: synthetic SEED-* lines always count; other settlements in the invoice month."""
    if received_at is None:
        return department_spent(entries, department)
    year, month = received_at.year, received_at.month
    selected = []
    for entry in _counted(entries):
        if entry.department != department:
            continue
        if entry.invoice_number.startswith("SEED-"):
            selected.append(entry)
            continue
        stamp = _received(entry.received_at)
        if stamp is not None and stamp.year == year and stamp.month == month:
            selected.append(entry)
    return _sum_known(selected)


def beneficiary_window_entries(
    entries: tuple[LedgerEntry, ...],
    beneficiary_norm: str | None,
    received_at: datetime | None,
    window_days: int,
) -> tuple[LedgerEntry, ...]:
    """T5.13 R21: counted lines of the same beneficiary within ``window_days``."""
    if beneficiary_norm is None or received_at is None:
        return ()
    selected = []
    for entry in _counted(entries):
        if normalize_beneficiary(entry.beneficiary) != beneficiary_norm:
            continue
        stamp = _received(entry.received_at)
        if stamp is None or abs((received_at - stamp).total_seconds()) <= window_days * 86400:
            # An unreadable date counts inside the window (fail closed).
            selected.append(entry)
    return tuple(selected)


def sum_amount_base(entries: tuple[LedgerEntry, ...]) -> float | None:
    return _sum_known(entries)


def duplicate_match(
    entries: tuple[LedgerEntry, ...],
    beneficiary_norm: str | None,
    invoice_number: str | None,
    amount: float | None,
    currency: str | None,
    received_at: datetime | None,
) -> DuplicateMatch | None:
    """Exact: same normalized beneficiary + same normalized invoice number.

    Probable: same beneficiary + same amount/currency + different number
    within 30 days (by received_at). Compares against every entry it is given:
    the caller passes the whole settled history (T5.13, D063), not only lines
    dated before this invoice.
    """
    number_norm = normalize_invoice_number(invoice_number)
    if beneficiary_norm is None or number_norm is None:
        return None
    probable: DuplicateMatch | None = None
    for entry in entries:
        if normalize_beneficiary(entry.beneficiary) != beneficiary_norm:
            continue
        if normalize_invoice_number(entry.invoice_number) == number_norm:
            return "exact"
        if (
            amount is not None
            and currency is not None
            and entry.amount_base is not None
            and entry.amount_base == amount
            and entry.currency == currency
            and received_at is not None
        ):
            stamp = _received(entry.received_at)
            if stamp is not None and abs((received_at - stamp).days) <= 30:
                probable = "probable"
    return probable
