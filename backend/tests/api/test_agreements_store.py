"""T9.1 (D061) — Vendor agreement registry persistence, both backends.

`MemoryStore` and `SqlStore` must behave identically here, same convention as
the rest of this file's T4.2/T5.10 siblings: solo-anexar versions, conflict
with hand-written rules, `expected_version` conflicts (including after a
`deactivate`, which does not reset the version counter), and one
`agreement_change` chain entry per confirm/deactivate that `verify_chain`
catches tampering with.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.api.store import (
    AgreementNotFoundError,
    AgreementVersionConflictError,
    MemoryStore,
)
from app.models.agreement import RetainerAgreement
from app.persistence import init_database
from app.persistence.sql_store import SqlStore
from app.persistence.tables import ChainEntryRow
from app.rules.agreements import AgreementConflictError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from tests.api.support import load_rules, rules_payload

_AGREEMENT = {
    "vendor_name": "Globex LLC",
    "currency": "USD",
    "periodicity": "monthly",
    "amount": {"min": 800, "max": 800},
    "valid_from": "2026-01-01",
    "valid_to": "2026-03-31",
}


def _memory_store():
    return MemoryStore(load_rules())


def _sql_store(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/agreements.sqlite")
    init_database(engine)
    store = SqlStore(engine)
    store.put_rules(load_rules())
    return store


@pytest.fixture(params=["memory", "sql"])
def store(request, tmp_path):
    return _memory_store() if request.param == "memory" else _sql_store(tmp_path)


def test_confirm_creates_active_v1(store) -> None:
    agreement = RetainerAgreement.model_validate(_AGREEMENT)
    version = store.confirm_agreement(
        "globex",
        terms=agreement,
        confirmed_by="cfo@demo.test",
        expected_version=0,
        source_sha256="abc",
        spans={"vendor_name": "cita"},
        at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert version.version == 1
    assert version.status == "active"
    assert store.get_active_agreement_version("globex").version == 1
    assert [a.agreement.vendor_key for a in store.list_active_agreements()] == ["globex"]


def test_reconfirm_supersedes_previous_version(store) -> None:
    agreement = RetainerAgreement.model_validate(_AGREEMENT)
    store.confirm_agreement(
        "globex", terms=agreement, confirmed_by="cfo@demo.test", expected_version=0,
        source_sha256=None, spans={}, at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    store.confirm_agreement(
        "globex", terms=agreement, confirmed_by="cfo@demo.test", expected_version=1,
        source_sha256=None, spans={}, at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    versions = store.list_agreement_versions("globex")
    assert [(v.version, v.status) for v in versions] == [(1, "superseded"), (2, "active")]


def test_wrong_expected_version_conflicts(store) -> None:
    agreement = RetainerAgreement.model_validate(_AGREEMENT)
    with pytest.raises(AgreementVersionConflictError):
        store.confirm_agreement(
            "globex", terms=agreement, confirmed_by="cfo@demo.test", expected_version=5,
            source_sha256=None, spans={}, at=datetime.now(UTC),
        )


def test_deactivate_then_reconfirm_requires_latest_version_not_zero(store) -> None:
    """Regression: after deactivate (no active row), expected_version must
    still be the real latest version number, never reset to 0."""
    agreement = RetainerAgreement.model_validate(_AGREEMENT)
    store.confirm_agreement(
        "globex", terms=agreement, confirmed_by="cfo@demo.test", expected_version=0,
        source_sha256=None, spans={}, at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    store.deactivate_agreement(
        "globex", author="cfo@demo.test", at=datetime(2026, 1, 2, tzinfo=UTC)
    )
    assert store.get_active_agreement_version("globex") is None

    with pytest.raises(AgreementVersionConflictError) as excinfo:
        store.confirm_agreement(
            "globex", terms=agreement, confirmed_by="cfo@demo.test", expected_version=0,
            source_sha256=None, spans={}, at=datetime.now(UTC),
        )
    assert excinfo.value.actual == 2

    revived = store.confirm_agreement(
        "globex", terms=agreement, confirmed_by="cfo@demo.test", expected_version=2,
        source_sha256=None, spans={}, at=datetime(2026, 1, 3, tzinfo=UTC),
    )
    assert revived.version == 3
    assert revived.status == "active"


def test_deactivate_unknown_vendor_raises_not_found(store) -> None:
    with pytest.raises(AgreementNotFoundError):
        store.deactivate_agreement("nope", author="cfo@demo.test", at=datetime.now(UTC))


def test_conflict_with_hand_written_rules_raises(store) -> None:
    payload = rules_payload()
    payload["payment_series"] = [
        {
            "id": "manual-globex",
            "beneficiary": "Globex LLC",
            "periodicity": "monthly",
            "currency": "USD",
            "expected_amount": {"min": 800, "max": 800},
            "start": "2026-01-01",
        }
    ]
    from app.models.rules_config import RulesConfig

    store.put_rules(RulesConfig.model_validate(payload))

    agreement = RetainerAgreement.model_validate(_AGREEMENT)
    with pytest.raises(AgreementConflictError):
        store.confirm_agreement(
            "globex", terms=agreement, confirmed_by="cfo@demo.test", expected_version=0,
            source_sha256=None, spans={}, at=datetime.now(UTC),
        )


def test_verify_chain_ok_after_confirm_and_deactivate(store) -> None:
    agreement = RetainerAgreement.model_validate(_AGREEMENT)
    store.confirm_agreement(
        "globex", terms=agreement, confirmed_by="cfo@demo.test", expected_version=0,
        source_sha256=None, spans={}, at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    store.deactivate_agreement(
        "globex", author="cfo@demo.test", at=datetime(2026, 1, 2, tzinfo=UTC)
    )
    result = store.verify_chain()
    assert result.ok is True
    assert result.length == 2


def test_tampered_agreement_change_entry_breaks_chain(tmp_path) -> None:
    store = _sql_store(tmp_path)
    agreement = RetainerAgreement.model_validate(_AGREEMENT)
    store.confirm_agreement(
        "globex", terms=agreement, confirmed_by="cfo@demo.test", expected_version=0,
        source_sha256=None, spans={}, at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert store.verify_chain().ok is True

    engine = store._engine  # noqa: SLF001 — direct-DB tamper, same pattern as sibling tests.
    with Session(engine) as session:
        row = session.scalar(
            select(ChainEntryRow).where(ChainEntryRow.kind == "agreement_change")
        )
        row.payload = row.payload.replace('"active"', '"inactive"')
        session.commit()

    result = store.verify_chain()
    assert result.ok is False
    assert result.first_broken_id == "globex:v1"
