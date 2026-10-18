"""T5.10 (D055) — pure, append-only hash-chain functions.

`compute_decision_entry_hash`/`compute_human_event_entry_hash`/`verify_chain`
live in `app.records.chain` and never touch SQLAlchemy or FastAPI; this file
proves them deterministic, sensitive to every relevant field, and -- the
point of an append-only log -- that a decision's hash is unaffected by a
later `human_events` append (excluded from what is hashed) while any OTHER
field change still breaks it.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from app.models.domain import DecisionRecord, HumanEvent
from app.records.chain import (
    GENESIS_PREV_HASH,
    canonical_json,
    compute_decision_entry_hash,
    compute_entry_hash,
    compute_human_event_entry_hash,
    decision_entry_payload,
    human_event_entry_payload,
    verify_chain,
)

_PAYLOAD: dict[str, object] = {
    "id": "dec_0042",
    "invoice_id": "INV-0042",
    "received_at": "2026-03-04T10:15:00Z",
    "decision": "ESCALAR",
    "severity": 1,
    "summary": "Escalada: USD 4.200 llega al umbral de aprobación humana.",
    "extracted": {
        "beneficiary": "Globex LLC",
        "amount": 4200.0,
        "currency": "USD",
        "amount_base": 4200.0,
        "fx": {"rate": 1.0, "date": "2026-03-01"},
        "due_date": "2026-03-20",
        "invoice_number": "GX-2231",
        "recipient": "Acme Demo Inc.",
        "source_spans": {"amount": "Total a pagar: USD 4.200,00"},
    },
    "checks": [
        {
            "rule": "R04",
            "name": "Aprobación humana por monto",
            "result": "FALLA",
            "detail": "USD 4.200 llega al umbral de USD 3.000.",
            "on_fail": "ESCALAR",
        }
    ],
    "jev_signals": [],
    "verifier": {"consistent": True, "issues": []},
    "admin_notice": None,
    "next_step": "Pendiente de aprobación de cfo@demo.test.",
    "trace": {"langsmith_run_id": None, "url": None},
    "versions": {
        "rules_version": "v3",
        "model_extractor": "extractor-demo",
        "model_verifier": "verifier-demo",
        "jev": "jev-demo",
    },
    "human_events": [],
}


def _record(**overrides: object) -> DecisionRecord:
    payload = {**_PAYLOAD, **overrides}
    return DecisionRecord.model_validate(payload)


def _event(**overrides: object) -> HumanEvent:
    payload: dict[str, object] = {
        "author": "cfo@demo.test",
        "at": datetime(2026, 3, 4, 12, 0, tzinfo=UTC),
        "action": "aprobada_humano",
        "reason": "Coincide con el presupuesto",
        **overrides,
    }
    return HumanEvent.model_validate(payload)


def test_genesis_prev_hash_is_64_zeros() -> None:
    assert GENESIS_PREV_HASH == "0" * 64
    assert len(GENESIS_PREV_HASH) == 64


def test_canonical_json_has_sorted_keys_and_no_whitespace() -> None:
    record = _record()
    text = canonical_json(decision_entry_payload(record))

    # Re-serializing the *parsed* structure with compact (",", ":") separators
    # and sorted keys must round-trip byte-for-byte: this proves there is no
    # JSON *structural* whitespace and keys are sorted, while still tolerating
    # whitespace that is part of an actual string value, like "USD 4.200".
    expected = json.dumps(
        json.loads(text), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert text == expected
    assert "\n" not in text
    # A top-level key ("decision") must appear before a later one ("summary")
    # once keys are sorted, independent of model field-declaration order.
    assert text.index('"decision"') < text.index('"summary"')


def test_decision_entry_payload_excludes_human_events() -> None:
    record = _record(human_events=[])
    payload = decision_entry_payload(record)

    assert "human_events" not in payload


def test_decision_entry_payload_is_unaffected_by_appended_human_events() -> None:
    before = _record(human_events=[])
    after = before.model_copy(update={"human_events": [_event()]})

    assert decision_entry_payload(before) == decision_entry_payload(after)


def test_compute_decision_entry_hash_is_deterministic() -> None:
    first = compute_decision_entry_hash(_record(), GENESIS_PREV_HASH)
    second = compute_decision_entry_hash(_record(), GENESIS_PREV_HASH)

    assert first == second
    assert len(first) == 64  # sha256 hex digest


def test_compute_decision_entry_hash_changes_when_a_non_human_events_field_changes() -> None:
    base = compute_decision_entry_hash(_record(), GENESIS_PREV_HASH)
    changed = compute_decision_entry_hash(
        _record(summary="Otro resumen distinto."), GENESIS_PREV_HASH
    )

    assert base != changed


def test_compute_decision_entry_hash_is_unchanged_by_a_later_human_event_append() -> None:
    """The exact property that makes the chain append-only: a legitimate
    approve/reject must never require rewriting this decision's own hash."""
    before = _record(human_events=[])
    after = before.model_copy(update={"human_events": [_event()]})

    hash_before = compute_decision_entry_hash(before, GENESIS_PREV_HASH)
    hash_after = compute_decision_entry_hash(after, GENESIS_PREV_HASH)

    assert hash_before == hash_after


def test_compute_decision_entry_hash_changes_when_prev_hash_changes() -> None:
    record = _record()

    base = compute_decision_entry_hash(record, GENESIS_PREV_HASH)
    other = compute_decision_entry_hash(record, "1" * 64)

    assert base != other


def test_human_event_entry_payload_is_the_full_event() -> None:
    event = _event()
    payload = human_event_entry_payload(event)

    assert payload["author"] == "cfo@demo.test"
    assert payload["action"] == "aprobada_humano"
    assert payload["reason"] == "Coincide con el presupuesto"


def test_compute_human_event_entry_hash_changes_when_the_event_changes() -> None:
    base = compute_human_event_entry_hash(_event(), GENESIS_PREV_HASH)
    changed = compute_human_event_entry_hash(
        _event(reason="Otro motivo."), GENESIS_PREV_HASH
    )

    assert base != changed


def test_compute_entry_hash_concatenates_prev_hash_before_canonical_json() -> None:
    payload = {"a": 1}
    expected = compute_entry_hash(payload, GENESIS_PREV_HASH)

    import hashlib

    manual = hashlib.sha256((GENESIS_PREV_HASH + canonical_json(payload)).encode("utf-8"))
    assert expected == manual.hexdigest()


def _chained_decision_entries(n: int) -> list[tuple[str, object, str, str]]:
    entries: list[tuple[str, object, str, str]] = []
    prev_hash = GENESIS_PREV_HASH
    for i in range(n):
        record = _record(id=f"dec_{i}", invoice_id=f"INV-{i}")
        payload = decision_entry_payload(record)
        record_hash = compute_entry_hash(payload, prev_hash)
        entries.append((record.id, payload, prev_hash, record_hash))
        prev_hash = record_hash
    return entries


def test_verify_chain_of_three_untouched_decisions_is_ok() -> None:
    result = verify_chain(_chained_decision_entries(3))

    assert result.ok is True
    assert result.length == 3
    assert result.first_broken_id is None


def test_verify_chain_detects_tampered_entry_at_its_exact_ref_id() -> None:
    entries = _chained_decision_entries(3)
    ref_id, payload, prev_hash, stored_hash = entries[1]
    tampered_payload = {**payload, "summary": "Resumen alterado sin recalcular hash."}
    entries[1] = (ref_id, tampered_payload, prev_hash, stored_hash)

    result = verify_chain(entries)

    assert result.ok is False
    assert result.length == 3
    assert result.first_broken_id == ref_id


def test_verify_chain_detects_a_deleted_entry() -> None:
    entries = _chained_decision_entries(3)
    del entries[1]  # simulate a direct DELETE of the middle entry

    result = verify_chain(entries)

    assert result.ok is False
    assert result.length == 2
    assert result.first_broken_id == entries[1][0]


def test_verify_chain_mixes_decision_and_human_event_entries() -> None:
    decision = _record(id="dec_0", invoice_id="INV-0")
    decision_payload = decision_entry_payload(decision)
    decision_hash = compute_entry_hash(decision_payload, GENESIS_PREV_HASH)

    event = _event()
    event_payload = human_event_entry_payload(event)
    event_hash = compute_entry_hash(event_payload, decision_hash)

    entries: list[tuple[str, object, str, str]] = [
        ("dec_0", decision_payload, GENESIS_PREV_HASH, decision_hash),
        ("dec_0", event_payload, decision_hash, event_hash),
    ]

    result = verify_chain(entries)

    assert result.ok is True
    assert result.length == 2
