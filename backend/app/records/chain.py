"""Append-only, tamper-evident hash chain (T5.10, D055).

Pure functions only: no I/O, no SQLAlchemy, no FastAPI. The persistence layer
(`app.persistence.sql_store`, `app.api.store`) calls these to append and
verify chain entries; this module never reads or writes a table.

Design (revised after review -- see the implementation report for this
task): a tamper-evident log must be append-only. An earlier version of this
module recomputed and overwrote a decision's `record_hash` whenever a human
event (approve/reject) was appended to it, then cascaded that rewrite into
every later entry's `prev_hash` too -- that is rehashing history, exactly
what an attacker tampering with the table would also do, so a verifier
cannot tell the two apart. This version never updates a stored hash:

- A **decision** entry hashes the record's own fields *excluding*
  `human_events` (that field is mutable -- more events can be appended to it
  later by legitimate approve/reject actions) over `prev_hash`. Because the
  hash excludes the one field that changes, re-hashing the *current* stored
  record (minus `human_events`) at verify time always reproduces the exact
  same hash computed once at insert time -- no rewrite is ever needed, and
  any OTHER field changing (a direct-DB tamper) still breaks the chain.
- A **human event** is its own, separate, append-only entry: approve/reject
  never mutates a decision's chain entry, it appends a new one with the
  event's own hash. That entry's data (author, action, reason, timestamp)
  never changes once appended, so it is hashed as-is, in full.

This does not change what `decide()` decides (R01-R13 untouched) and does
not add fields to `DecisionRecord` (frozen, D013): hashing is persistence
metadata over the already-decided record, never an input to any rule.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.models.domain import DecisionRecord, HumanEvent

GENESIS_PREV_HASH = "0" * 64


@dataclass(frozen=True)
class ChainVerification:
    """Result of walking the append-only chain in `seq` order.

    `ok=True` and `first_broken_id=None` mean every stored entry's hash
    matches what `compute_entry_hash` recomputes from that entry's current
    stored data and the running `prev_hash`, chained from `GENESIS_PREV_HASH`.
    On the first mismatch, `ok=False` and `first_broken_id` is that entry's
    `ref_id` (a decision id, for either a `decision` or a `human_event`
    entry); the walk stops there (GET /decisions/verify-chain, T5.10, D055).
    """

    ok: bool
    length: int
    first_broken_id: str | None


def canonical_json(payload: Any) -> str:
    """Deterministic JSON for `payload`: sorted keys, no whitespace, UTF-8 text.

    `payload` must already be JSON-safe (str/int/float/bool/None/list/dict),
    e.g. the output of `model_dump(mode="json")`. `sort_keys=True` fixes key
    order independent of dict insertion order, so the same logical content
    always produces the same string.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_entry_hash(payload: Any, prev_hash: str) -> str:
    """SHA-256 hex digest of `prev_hash + canonical_json(payload)`, UTF-8 encoded.

    Deterministic for the same `(payload, prev_hash)` pair; changes if any
    part of `payload` changes, and changes if `prev_hash` changes. The first
    entry of the whole chain chains from `GENESIS_PREV_HASH` (64 zeros).
    """
    digest_input = (prev_hash + canonical_json(payload)).encode("utf-8")
    return hashlib.sha256(digest_input).hexdigest()


def decision_entry_payload(record: DecisionRecord) -> dict[str, Any]:
    """The part of `record` a decision's chain entry hashes: every field
    except `human_events`, which is mutable (future approve/reject actions
    append to it) and must never affect this entry's hash.
    """
    data = record.model_dump(mode="json")
    data.pop("human_events", None)
    return data


def human_event_entry_payload(event: HumanEvent) -> dict[str, Any]:
    """The part of a human event's chain entry that gets hashed: the event
    in full. Once appended this never changes, so nothing is excluded.
    """
    return event.model_dump(mode="json")


def compute_decision_entry_hash(record: DecisionRecord, prev_hash: str) -> str:
    """Hash for a new `decision` chain entry (append-only; never recomputed
    and stored again after a later human event -- see module docstring)."""
    return compute_entry_hash(decision_entry_payload(record), prev_hash)


def compute_human_event_entry_hash(event: HumanEvent, prev_hash: str) -> str:
    """Hash for a new `human_event` chain entry."""
    return compute_entry_hash(human_event_entry_payload(event), prev_hash)


@dataclass(frozen=True)
class AllowlistChangePayload:
    """Immutable payload for T7.4 `allowlist_change` chain entries (D059)."""

    beneficiary: str
    author: str
    reason: str
    at: datetime
    source_decision_id: str


def allowlist_change_entry_payload(change: AllowlistChangePayload) -> dict[str, Any]:
    """Full payload hashed for an `allowlist_change` entry (append-only)."""
    return {
        "beneficiary": change.beneficiary,
        "author": change.author,
        "reason": change.reason,
        "at": change.at.isoformat().replace("+00:00", "Z"),
        "source_decision_id": change.source_decision_id,
    }


def compute_allowlist_change_entry_hash(change: AllowlistChangePayload, prev_hash: str) -> str:
    return compute_entry_hash(allowlist_change_entry_payload(change), prev_hash)


@dataclass(frozen=True)
class AgreementChangePayload:
    """Immutable payload for T9.1 `agreement_change` chain entries (D061, same
    append-only pattern as `AllowlistChangePayload`, T7.4/D058). `terms_hash`
    (not the full `terms_json`) keeps this entry small and stable; the version
    row itself (`vendor_agreement_version`) holds the full confirmed terms.
    """

    vendor_key: str
    version: int
    status: str
    confirmed_by: str
    confirmed_at: datetime
    terms_hash: str
    source_sha256: str | None


def agreement_change_entry_payload(change: AgreementChangePayload) -> dict[str, Any]:
    """Full payload hashed for an `agreement_change` entry (append-only)."""
    return {
        "vendor_key": change.vendor_key,
        "version": change.version,
        "status": change.status,
        "confirmed_by": change.confirmed_by,
        "confirmed_at": change.confirmed_at.isoformat().replace("+00:00", "Z"),
        "terms_hash": change.terms_hash,
        "source_sha256": change.source_sha256,
    }


def compute_agreement_change_entry_hash(change: AgreementChangePayload, prev_hash: str) -> str:
    return compute_entry_hash(agreement_change_entry_payload(change), prev_hash)


def verify_chain(entries: list[tuple[str, Any, str, str]]) -> ChainVerification:
    """Recompute the chain over `entries` (already ordered by `seq`).

    Each entry is `(ref_id, payload, stored_prev_hash, stored_record_hash)`:
    `payload` is whatever the caller recomputed from *current* stored data
    for that entry (see `SqlStore.verify_chain`/`MemoryStore.verify_chain` --
    a `decision` entry's payload is re-derived from the live decision record
    minus `human_events`; a `human_event` entry's payload is its own stored,
    immutable data). Shared by both backends so there is exactly one
    walking/comparison implementation (GET /decisions/verify-chain, T5.10,
    D055). A deleted entry is caught too: the next surviving entry's stored
    `prev_hash` will no longer equal the hash this walk just recomputed, so
    the break surfaces there.
    """
    expected_prev = GENESIS_PREV_HASH
    for ref_id, payload, stored_prev_hash, stored_record_hash in entries:
        if stored_prev_hash != expected_prev:
            return ChainVerification(ok=False, length=len(entries), first_broken_id=ref_id)
        computed = compute_entry_hash(payload, expected_prev)
        if computed != stored_record_hash:
            return ChainVerification(ok=False, length=len(entries), first_broken_id=ref_id)
        expected_prev = stored_record_hash
    return ChainVerification(ok=True, length=len(entries), first_broken_id=None)
