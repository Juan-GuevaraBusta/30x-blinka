"""In-memory rules, decisions, and human events. Disk and SQL are T4.2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.models.domain import DecisionRecord, HumanEvent
from app.models.rules_config import RulesConfig, VendorAddition
from app.records.chain import (
    GENESIS_PREV_HASH,
    AllowlistChangePayload,
    ChainVerification,
    allowlist_change_entry_payload,
    compute_decision_entry_hash,
    compute_entry_hash,
    decision_entry_payload,
    human_event_entry_payload,
)
from app.records.chain import verify_chain as _verify_chain_entries
from app.rules.normalize import normalize_beneficiary


class DuplicateDecisionError(Exception):
    def __init__(self, invoice_id: str) -> None:
        super().__init__(invoice_id)
        self.invoice_id = invoice_id


class VendorOnboardingDisabledError(Exception):
    """T7.4: `vendor_onboarding` missing or not enabled."""


class R01NotFailedError(Exception):
    """T7.4: source decision does not carry R01 in FALLA."""


class AlreadyAllowedError(Exception):
    """T7.4: beneficiary already on the allowlist."""


@dataclass(frozen=True)
class _ChainEntry:
    """One append-only chain entry (T5.10, D055), mirroring
    `app.persistence.tables.ChainEntryRow` for this in-memory backend.

    `payload` is `None` for a `decision` entry -- `MemoryStore.verify_chain`
    re-derives what to hash from the *current* `self.decisions[ref_id]`
    (minus `human_events`) instead, same as `SqlStore.verify_chain` re-reads
    the live `DecisionRecordRow`. For a `human_event` entry, `payload` is
    that event's own data, stored once and never touched again.
    """

    kind: str
    ref_id: str
    payload: dict[str, Any] | None
    prev_hash: str
    record_hash: str


class MemoryStore:
    def __init__(self, rules: RulesConfig) -> None:
        self.rules = rules
        self.decisions: dict[str, DecisionRecord] = {}
        self._owners: dict[str, str] = {}
        self._invoice_keys: set[tuple[str, str]] = set()
        # T5.10 (D055): append-only chain, same shape as SqlStore's
        # `chain_entries` table. Entries are appended in `add_decision` and
        # `add_human_event` and never rewritten afterward -- see
        # `app.records.chain`'s module docstring for why.
        self._chain: list[_ChainEntry] = []

    def put_rules(self, rules: RulesConfig) -> RulesConfig:
        """Replace rules only. Caller must pass an already validated `RulesConfig`."""
        self.rules = rules
        return self.rules

    def has_invoice(self, invoice_id: str, owner_id: str) -> bool:
        return (owner_id, invoice_id) in self._invoice_keys

    def list_decisions_for_owner(
        self, owner_id: str, decision: str | None = None
    ) -> list[DecisionRecord]:
        records = [
            record
            for record_id, record in self.decisions.items()
            if self._owners.get(record_id) == owner_id
        ]
        if decision is None:
            return records
        return [item for item in records if item.decision == decision]

    def get_for_owner(self, decision_id: str, owner_id: str) -> DecisionRecord | None:
        if self._owners.get(decision_id) != owner_id:
            return None
        return self.decisions.get(decision_id)

    def _chain_tip(self) -> str:
        return self._chain[-1].record_hash if self._chain else GENESIS_PREV_HASH

    def add_decision(
        self, record: DecisionRecord, owner_id: str = "test-user-id"
    ) -> DecisionRecord:
        key = (owner_id, record.invoice_id)
        if record.id in self.decisions or key in self._invoice_keys:
            raise DuplicateDecisionError(record.invoice_id)
        self.decisions[record.id] = record
        self._owners[record.id] = owner_id
        self._invoice_keys.add(key)
        # Append-only: chain from the current tip, inside the same call
        # `SqlStore.add_decision` chains inside its session -- both run
        # under the T5.8 `_INVOICE_LOCK`, so ordering is deterministic.
        prev_hash = self._chain_tip()
        record_hash = compute_decision_entry_hash(record, prev_hash)
        self._chain.append(
            _ChainEntry(
                kind="decision", ref_id=record.id, payload=None,
                prev_hash=prev_hash, record_hash=record_hash,
            )
        )
        return record

    def get(self, decision_id: str) -> DecisionRecord | None:
        return self.decisions.get(decision_id)

    def add_human_event(self, decision_id: str, event: HumanEvent) -> DecisionRecord:
        """Copy the record. The previous object stays unchanged for any other holder."""
        current = self.decisions[decision_id]
        updated = current.model_copy(update={"human_events": [*current.human_events, event]})
        self.decisions[decision_id] = updated
        # Append-only: a NEW `human_event` entry, never a rewrite of this
        # decision's existing entry (see `SqlStore.add_human_event`).
        prev_hash = self._chain_tip()
        event_payload = human_event_entry_payload(event)
        record_hash = compute_entry_hash(event_payload, prev_hash)
        self._chain.append(
            _ChainEntry(
                kind="human_event", ref_id=decision_id, payload=event_payload,
                prev_hash=prev_hash, record_hash=record_hash,
            )
        )
        return updated

    def add_beneficiary_from_decision(
        self,
        decision_id: str,
        *,
        author: str,
        reason: str,
        at: datetime,
    ) -> RulesConfig:
        """T7.4 (D059): append allowlist + `allowlist_change`; decision row unchanged."""
        onboarding = self.rules.vendor_onboarding
        if onboarding is None or not onboarding.enabled:
            raise VendorOnboardingDisabledError()
        record = self.decisions.get(decision_id)
        if record is None:
            raise KeyError(decision_id)
        if not any(c.rule == "R01" and c.result == "FALLA" for c in record.checks):
            raise R01NotFailedError()
        beneficiary = (record.extracted.beneficiary or "").strip()
        if not beneficiary:
            raise ValueError("missing_beneficiary")
        allowed = {normalize_beneficiary(name) for name in self.rules.allowed_beneficiaries}
        if normalize_beneficiary(beneficiary) in allowed:
            raise AlreadyAllowedError()
        addition = VendorAddition(
            beneficiary=beneficiary,
            added_at=at,
            added_by=author,
            reason=reason,
            source_decision_id=decision_id,
        )
        updated_rules = self.rules.model_copy(
            update={
                "allowed_beneficiaries": [*self.rules.allowed_beneficiaries, beneficiary],
                "vendor_additions": [*self.rules.vendor_additions, addition],
            }
        )
        self.rules = updated_rules
        change = AllowlistChangePayload(
            beneficiary=beneficiary,
            author=author,
            reason=reason,
            at=at,
            source_decision_id=decision_id,
        )
        prev_hash = self._chain_tip()
        payload = allowlist_change_entry_payload(change)
        record_hash = compute_entry_hash(payload, prev_hash)
        self._chain.append(
            _ChainEntry(
                kind="allowlist_change",
                ref_id=decision_id,
                payload=payload,
                prev_hash=prev_hash,
                record_hash=record_hash,
            )
        )
        return updated_rules

    def verify_chain(self) -> ChainVerification:
        """GET /decisions/verify-chain (T5.10, D055) for this in-memory backend.

        Walks `self._chain` in append order and, for each entry, recomputes
        its hash from *current* stored data -- a `decision` entry re-reads
        `self.decisions[ref_id]` (minus `human_events`); a `human_event`
        entry re-reads its own stored, immutable payload. A direct-store
        tamper is demonstrated by mutating `self.decisions` or `self._chain`
        directly, bypassing this class's own methods -- exactly like editing
        `DecisionRecordRow`/`ChainEntryRow` through a raw `Session` bypasses
        `SqlStore`. A ``ref_id`` removed from ``self.decisions`` (simulating
        a deleted row) is reported as the break point instead of raising out
        of this read-only endpoint.
        """
        entries: list[tuple[str, object, str, str]] = []
        for entry in self._chain:
            if entry.kind == "decision":
                record = self.decisions.get(entry.ref_id)
                if record is None:
                    return ChainVerification(
                        ok=False, length=len(self._chain), first_broken_id=entry.ref_id
                    )
                payload: object = decision_entry_payload(record)
            else:
                if entry.payload is None:
                    return ChainVerification(
                        ok=False, length=len(self._chain), first_broken_id=entry.ref_id
                    )
                payload = entry.payload
            entries.append((entry.ref_id, payload, entry.prev_hash, entry.record_hash))
        return _verify_chain_entries(entries)
