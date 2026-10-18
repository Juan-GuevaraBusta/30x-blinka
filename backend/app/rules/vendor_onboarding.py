"""T7.4 (D059) — Vendor allowlist additions and R20 ledger queries."""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.rules_config import RulesConfig, VendorAddition
from app.rules.context import LedgerEntry
from app.rules.normalize import normalize_beneficiary


def find_vendor_addition(rules: RulesConfig, beneficiary: str | None) -> VendorAddition | None:
    norm = normalize_beneficiary(beneficiary)
    if norm is None:
        return None
    for row in rules.vendor_additions:
        if normalize_beneficiary(row.beneficiary) == norm:
            return row
    return None


def _received_at(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def has_vendor_human_approval_after(
    ledger: tuple[LedgerEntry, ...],
    beneficiary: str,
    added_at: datetime,
) -> bool:
    """True when the ledger has `aprobada_humano` for this vendor after `added_at`."""
    norm = normalize_beneficiary(beneficiary)
    if norm is None:
        return False
    added_stamp = added_at if added_at.tzinfo is not None else added_at.replace(tzinfo=UTC)
    for entry in ledger:
        if entry.decision != "aprobada_humano":
            continue
        if normalize_beneficiary(entry.beneficiary) != norm:
            continue
        stamp = _received_at(entry.received_at)
        if stamp is not None and stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=UTC)
        if stamp is not None and stamp > added_stamp:
            return True
    return False
