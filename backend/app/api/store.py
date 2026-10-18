"""In-memory rules, decisions, and human events. Disk and SQL are T4.2."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.models.agreement import VendorAgreement, VendorAgreementVersion, vendor_agreement_json
from app.models.domain import DecisionRecord, HumanEvent
from app.models.rules_config import RulesConfig, VendorAddition
from app.records.chain import (
    GENESIS_PREV_HASH,
    AgreementChangePayload,
    AllowlistChangePayload,
    ChainVerification,
    agreement_change_entry_payload,
    allowlist_change_entry_payload,
    compute_decision_entry_hash,
    compute_entry_hash,
    decision_entry_payload,
    human_event_entry_payload,
)
from app.records.chain import verify_chain as _verify_chain_entries
from app.rules.agreements import ActiveAgreement, vendor_key_conflicts_with_base
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


class AgreementVersionConflictError(Exception):
    """T9.1: `expected_version` does not match the vendor's current version."""

    def __init__(self, vendor_key: str, expected: int, actual: int) -> None:
        super().__init__(vendor_key)
        self.vendor_key = vendor_key
        self.expected = expected
        self.actual = actual


class AgreementNotFoundError(Exception):
    """T9.1: no version exists yet for this `vendor_key`."""

    def __init__(self, vendor_key: str) -> None:
        super().__init__(vendor_key)
        self.vendor_key = vendor_key


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
        # T9.1 (D061): solo-anexar version history per vendor_key, same shape
        # as SqlStore's `vendor_agreement_version` table. A confirm appends a
        # new version and flips the previous `active` one to `superseded`;
        # nothing here is ever rewritten in place.
        self._agreement_versions: dict[str, list[VendorAgreementVersion]] = {}

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

    # --- T9.1 (D061): vendor agreement registry ---------------------------------

    def list_agreement_vendor_keys(self) -> list[str]:
        return sorted(self._agreement_versions.keys())

    def list_agreement_versions(self, vendor_key: str) -> list[VendorAgreementVersion]:
        """Oldest-first, mirroring insertion order (`version` ascending)."""
        return list(self._agreement_versions.get(vendor_key, []))

    def get_active_agreement_version(self, vendor_key: str) -> VendorAgreementVersion | None:
        for version in reversed(self._agreement_versions.get(vendor_key, [])):
            if version.status == "active":
                return version
        return None

    def list_active_agreements(self) -> list[ActiveAgreement]:
        """Every vendor's current `active` version, for `compile_rules` (§4)."""
        result: list[ActiveAgreement] = []
        for vendor_key in self._agreement_versions:
            active = self.get_active_agreement_version(vendor_key)
            if active is not None:
                result.append(
                    ActiveAgreement(
                        agreement=active.terms,
                        version=active.version,
                        confirmed_by=active.confirmed_by,
                        spans=dict(active.spans),
                    )
                )
        return result

    def confirm_agreement(
        self,
        vendor_key: str,
        *,
        terms: VendorAgreement,
        confirmed_by: str,
        expected_version: int,
        source_sha256: str | None,
        spans: dict[str, str],
        at: datetime,
    ) -> VendorAgreementVersion:
        """§3 `PUT /agreements/{vendor_key}`: append a new `active` version,
        supersede the previous one (if any), and append one `agreement_change`
        chain entry (§2, same append-only pattern as T7.4's `allowlist_change`).
        """
        from app.rules.agreements import AgreementConflictError

        if vendor_key_conflicts_with_base(self.rules, vendor_key):
            raise AgreementConflictError(vendor_key)

        existing = self._agreement_versions.setdefault(vendor_key, [])
        # `current_version` is the latest version number ever assigned to this
        # vendor_key, regardless of status -- a confirm after a `deactivate`
        # (no `active` row) must still require the real latest version, not
        # reset to 0 and collide with an already-used version number.
        current_version = existing[-1].version if existing else 0
        if expected_version != current_version:
            raise AgreementVersionConflictError(vendor_key, expected_version, current_version)

        current_active = self.get_active_agreement_version(vendor_key)
        if current_active is not None:
            superseded = current_active.model_copy(update={"status": "superseded"})
            existing[existing.index(current_active)] = superseded

        new_version = VendorAgreementVersion(
            vendor_key=vendor_key,
            version=current_version + 1,
            terms=terms,
            source_sha256=source_sha256,
            spans=dict(spans),
            confirmed_by=confirmed_by,
            confirmed_at=at,
            status="active",
        )
        existing.append(new_version)

        self._append_agreement_change(new_version)
        return new_version

    def deactivate_agreement(
        self, vendor_key: str, *, author: str, at: datetime
    ) -> VendorAgreementVersion:
        """§3 `POST /agreements/{vendor_key}/deactivate`: a new `inactive`
        version, carrying forward the last confirmed terms for audit.
        """
        current = self.get_active_agreement_version(vendor_key)
        if current is None:
            raise AgreementNotFoundError(vendor_key)

        existing = self._agreement_versions[vendor_key]
        existing[existing.index(current)] = current.model_copy(update={"status": "superseded"})

        new_version = VendorAgreementVersion(
            vendor_key=vendor_key,
            version=current.version + 1,
            terms=current.terms,
            source_sha256=current.source_sha256,
            spans=dict(current.spans),
            confirmed_by=author,
            confirmed_at=at,
            status="inactive",
        )
        existing.append(new_version)

        self._append_agreement_change(new_version)
        return new_version

    def _append_agreement_change(self, version: VendorAgreementVersion) -> None:
        terms_hash = hashlib.sha256(
            vendor_agreement_json(version.terms).encode("utf-8")
        ).hexdigest()
        change = AgreementChangePayload(
            vendor_key=version.vendor_key,
            version=version.version,
            status=version.status,
            confirmed_by=version.confirmed_by,
            confirmed_at=version.confirmed_at,
            terms_hash=terms_hash,
            source_sha256=version.source_sha256,
        )
        prev_hash = self._chain_tip()
        payload = agreement_change_entry_payload(change)
        record_hash = compute_entry_hash(payload, prev_hash)
        self._chain.append(
            _ChainEntry(
                kind="agreement_change",
                ref_id=f"{version.vendor_key}:v{version.version}",
                payload=payload,
                prev_hash=prev_hash,
                record_hash=record_hash,
            )
        )
