"""T5.8 (D055): close the ledger-read -> decide -> persist TOCTOU race.

Two invoices, each individually under `limits.per_period`, can arrive at
almost the same time. Both read the same prior-settled ledger (neither sees
the other yet), both independently decide PAGAR, and both persist under
distinct `invoice_id`s -- the only duplicate guard in
`SqlStore.add_decision` does not stop them. Jointly they can exceed
`limits.per_period.amount`, which AGENTS.md invariant I1/I9 forbids
("cero pagos fuera de reglas").

This uses a `GraphDeps`/`run_invoice` double (no LLM) that evaluates the
*same* period-limit logic as R03, against whatever ledger it was handed, so
the test exercises the real race window instead of a scripted outcome.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime

import app.api.production_processor as production_processor_module
import pytest
from app.api.app import _decide_and_store_invoice
from app.api.production_processor import make_production_processor
from app.api.schemas import InvoiceUpload
from app.graph.deps import GraphDeps
from app.models.domain import Decision, DecisionRecord
from app.persistence import SqlStore, init_database, seed_rules
from app.rules.ledger_queries import period_paid_total
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import create_engine
from tests.api.support import RULES_PATH, make_record

# Widens the read -> decide -> persist window so two real OS threads can
# interleave without the lock. With the lock held, this only makes the test
# slower, never flaky: the mutex forces full serialization either way.
_SLEEP_SECONDS = 0.05


def _fake_factory(settings: object, rules: object, ledger: object) -> GraphDeps:
    return GraphDeps(
        extractor=object(),
        verifier=object(),
        jev=object(),
        rules=rules,  # type: ignore[arg-type]
        fx=object(),
        ledger=ledger,  # type: ignore[arg-type]
        company_name=rules.company.name,  # type: ignore[attr-defined]
        rules_version="v1",
        model_extractor="x",
        model_verifier="y",
        jev_label="z",
    )


def _fake_run_invoice(deps: GraphDeps, **kwargs: object) -> DecisionRecord:
    """No-LLM double: PAGAR iff the ledger it was handed is under the period limit.

    The returned record's `extracted.amount_base`/`received_at` must match the
    invoice's real amount/date: `settled_ledger_from_store` rebuilds the
    ledger from persisted *records*, not from the original upload, so a
    canned amount would hide the race this test exists to catch.
    """
    amount = float(kwargs["raw"].decode())  # type: ignore[union-attr]
    received_at: datetime = kwargs["received_at"]  # type: ignore[assignment]
    invoice_id: str = kwargs["invoice_id"]  # type: ignore[assignment]
    time.sleep(_SLEEP_SECONDS)
    total = period_paid_total(deps.ledger, received_at.year, received_at.month) + amount
    limit = deps.rules.limits.per_period.amount
    decision: Decision = "PAGAR" if total <= limit else deps.rules.on_fail.R03
    base = make_record(invoice_id=invoice_id, id=f"dec_{invoice_id}", decision=decision)
    extracted = base.extracted.model_copy(
        update={"amount": amount, "amount_base": amount, "invoice_number": invoice_id}
    )
    return base.model_copy(update={"received_at": received_at, "extracted": extracted})


def _make_store(tmp_path, name: str) -> SqlStore:
    db = tmp_path / name
    engine = create_engine(f"sqlite:///{db}")
    init_database(engine)
    store = SqlStore(engine)
    seed_rules(store, RULES_PATH)
    return store


def _uploads_over_period_limit(limit: float) -> tuple[InvoiceUpload, InvoiceUpload]:
    """Two invoices, each under `limit`, whose sum exceeds it."""
    per_invoice = limit * 0.75
    upload_a = InvoiceUpload(
        invoice_id="INV-RACE-A",
        channel="pdf_text",
        received_at=datetime.fromisoformat("2026-03-04T10:15:00+00:00"),
        content=str(per_invoice).encode(),
    )
    upload_b = InvoiceUpload(
        invoice_id="INV-RACE-B",
        channel="pdf_text",
        received_at=datetime.fromisoformat("2026-03-04T10:16:00+00:00"),
        content=str(per_invoice).encode(),
    )
    return upload_a, upload_b


def _run_concurrently(tmp_path, db_name: str) -> list[Decision]:
    store = _make_store(tmp_path, db_name)
    processor = make_production_processor(
        store,
        deps_factory=_fake_factory,
        checkpointer=MemorySaver(),
    )
    rules = store.rules
    limit = rules.limits.per_period.amount
    upload_a, upload_b = _uploads_over_period_limit(limit)

    results: dict[str, DecisionRecord | BaseException] = {}

    def _run(upload: InvoiceUpload) -> None:
        try:
            results[upload.invoice_id] = _decide_and_store_invoice(processor, store, upload)
        except BaseException as exc:  # noqa: BLE001 - captured for the assertion below
            results[upload.invoice_id] = exc

    threads = [
        threading.Thread(target=_run, args=(upload_a,)),
        threading.Thread(target=_run, args=(upload_b,)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    decisions: list[Decision] = []
    for invoice_id in (upload_a.invoice_id, upload_b.invoice_id):
        outcome = results[invoice_id]
        assert isinstance(outcome, DecisionRecord), f"{invoice_id} raised {outcome!r}"
        decisions.append(outcome.decision)
    return decisions


def test_concurrent_invoices_jointly_exceed_period_limit_at_most_one_pagar(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(production_processor_module, "run_invoice", _fake_run_invoice)
    decisions = _run_concurrently(tmp_path, "race.sqlite")

    assert decisions.count("PAGAR") <= 1, (
        f"both invoices settled PAGAR: {decisions} -- "
        "limits.per_period was jointly exceeded (I1/I9)"
    )
    on_fail = {"ESCALAR", "FRENAR"}
    for decision in decisions:
        if decision != "PAGAR":
            assert decision in on_fail


@pytest.mark.parametrize("attempt", range(20))
def test_concurrent_invoices_enforce_period_limit_repeatedly(
    tmp_path, monkeypatch: pytest.MonkeyPatch, attempt: int
) -> None:
    """Acceptance criterion #2 (T5_8_SPEC.md): not intermittent across 20 runs."""
    monkeypatch.setattr(production_processor_module, "run_invoice", _fake_run_invoice)
    decisions = _run_concurrently(tmp_path, f"race_{attempt}.sqlite")
    assert decisions.count("PAGAR") <= 1, f"attempt {attempt}: both settled PAGAR: {decisions}"
