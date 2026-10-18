"""T7.2 (D059) — Pure payment-series resolution for R15-R18. No LLM, no decide().

Each function here is a plain, deterministic transform over
`app.models.rules_config.PaymentSeries` and the ledger (`app.rules.context`).
Severity composition (R15-R18 can only ADD severity, never remove it) is
enforced structurally by `app.rules.run_checks.run_deterministic_checks`,
which only ever *appends* these checks -- never replaces or removes R01-R14.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.models.domain import Extraction
from app.models.rules_config import PaymentSeries
from app.rules.context import LedgerEntry
from app.rules.ledger_queries import COUNTED_DECISIONS
from app.rules.normalize import normalize_beneficiary

_CALENDAR_PERIODICITIES = frozenset({"monthly", "biweekly", "quarterly"})


@dataclass(frozen=True)
class SeriesResolution:
    """Which `PaymentSeries` (if any) this invoice belongs to (§2)."""

    series: PaymentSeries | None
    ambiguous: bool = False


def find_matching_series(
    payment_series: list[PaymentSeries], extraction: Extraction
) -> SeriesResolution:
    """First-class lookup: normalized beneficiary + (series' own) department.

    More than one series matching the same invoice is indeterminate (§2):
    silently picking one could hide a data-configuration mistake.
    """
    beneficiary_norm = normalize_beneficiary(extraction.beneficiary)
    if beneficiary_norm is None:
        return SeriesResolution(series=None)
    matches = [
        series
        for series in payment_series
        if normalize_beneficiary(series.beneficiary) == beneficiary_norm
        and (series.department is None or series.department == extraction.department)
    ]
    if len(matches) > 1:
        return SeriesResolution(series=None, ambiguous=True)
    if not matches:
        return SeriesResolution(series=None)
    return SeriesResolution(series=matches[0])


def _matching_items(series: PaymentSeries, due_date: date) -> list[str]:
    return [item.key for item in series.items if item.due_from <= due_date <= item.due_to]


def resolve_item_key(series: PaymentSeries, due_date: date) -> tuple[str | None, int]:
    """For installments/milestones: the single item containing `due_date`.

    Returns ``(key, 1)`` on exactly one match, ``(None, 0)`` when no item
    contains the date (out of series), and ``(None, n)`` for ``n >= 2``
    (ambiguous -- overlapping item windows in the configured series).
    """
    matches = _matching_items(series, due_date)
    if len(matches) == 1:
        return matches[0], 1
    return None, len(matches)


def period_key(series: PaymentSeries, due_date: date) -> str | None:
    """Pure period key (§2). ``None`` means "cannot be determined" (fail-closed).

    `monthly` -> ``YYYY-MM``; `quarterly` -> ``YYYY-Qn``; `biweekly` -> the
    index of the 14-day block counted from `start` (``Bn``);
    `installments`/`milestones` -> the single item key containing the date.
    """
    if series.periodicity == "monthly":
        return f"{due_date.year:04d}-{due_date.month:02d}"
    if series.periodicity == "quarterly":
        quarter = (due_date.month - 1) // 3 + 1
        return f"{due_date.year:04d}-Q{quarter}"
    if series.periodicity == "biweekly":
        if series.start is None or due_date < series.start:
            return None
        index = (due_date - series.start).days // 14
        return f"B{index}"
    key, count = resolve_item_key(series, due_date)
    return key if count == 1 else None


def paid_entries_for_series(
    entries: tuple[LedgerEntry, ...], series: PaymentSeries
) -> tuple[LedgerEntry, ...]:
    """Counted (PAGAR/aprobada_humano) ledger lines belonging to this series."""
    beneficiary_norm = normalize_beneficiary(series.beneficiary)
    return tuple(
        entry
        for entry in entries
        if entry.decision in COUNTED_DECISIONS
        and normalize_beneficiary(entry.beneficiary) == beneficiary_norm
        and (series.department is None or entry.department == series.department)
    )


def _month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _iter_monthly_keys(start: date, before: date) -> list[str]:
    keys: list[str] = []
    year, month = start.year, start.month
    while (year, month) < (before.year, before.month):
        keys.append(_month_key(year, month))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return keys


def _quarter(d: date) -> int:
    return (d.month - 1) // 3 + 1


def _iter_quarterly_keys(start: date, before: date) -> list[str]:
    keys: list[str] = []
    year, quarter = start.year, _quarter(start)
    before_year, before_quarter = before.year, _quarter(before)
    while (year, quarter) < (before_year, before_quarter):
        keys.append(f"{year:04d}-Q{quarter}")
        quarter += 1
        if quarter > 4:
            quarter = 1
            year += 1
    return keys


def _iter_biweekly_keys(start: date, before: date) -> list[str]:
    if before < start:
        return []
    before_index = (before - start).days // 14
    return [f"B{i}" for i in range(before_index)]


def expected_periods_before(series: PaymentSeries, due_date: date) -> list[str]:
    """Calendar period keys from `series.start` up to (excluding) `due_date`'s own (§3, R18).

    Only meaningful for calendar periodicities; installments/milestones
    report their own explicit items instead (no open-ended sequence to walk).
    """
    if series.start is None or series.periodicity not in _CALENDAR_PERIODICITIES:
        return []
    if series.periodicity == "monthly":
        return _iter_monthly_keys(series.start, due_date)
    if series.periodicity == "quarterly":
        return _iter_quarterly_keys(series.start, due_date)
    return _iter_biweekly_keys(series.start, due_date)
