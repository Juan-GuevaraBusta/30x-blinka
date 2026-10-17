"""T2.4 — Deterministic ledger: order, seed, settlement, catalog integration."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.models.domain import Extraction, JevSignal
from app.models.rules_config import RulesConfig, load_rules_config
from app.rules.context import ContractTerms, LedgerEntry, RuleContext
from app.rules.fx import FxTable, load_fx_table
from app.rules.ledger import Ledger, ledger_view_for_invoice
from app.rules.ledger_queries import (
    department_spent,
    duplicate_match,
    period_paid_total,
)
from app.rules.normalize import normalize_beneficiary, normalize_currency

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = REPO_ROOT / "data" / "invoices" / "catalog.json"


@pytest.fixture(scope="module")
def rules() -> RulesConfig:
    return load_rules_config(REPO_ROOT / "data" / "rules.json")


@pytest.fixture(scope="module")
def fx_table() -> FxTable:
    return load_fx_table(REPO_ROOT / "data" / "fx.json")


def _load_catalog() -> list[dict]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _catalog_by_id(catalog: list[dict], invoice_id: str) -> dict:
    for row in catalog:
        if row["id"] == invoice_id:
            return row
    raise KeyError(invoice_id)


def _signals(*ids: str, prob: float = 0.99) -> list[JevSignal]:
    return [JevSignal(id=jid, answer=True, probability=prob) for jid in ids]  # type: ignore[arg-type]


def make_context(
    rules: RulesConfig,
    fx_table: FxTable,
    *,
    beneficiary: str | None = "Globex LLC",
    amount: float | None = 800.0,
    currency: str | None = "USD",
    amount_base: float | None = 800.0,
    due_date: str | None = "2026-05-27",
    invoice_number: str | None = "INV-GX-TEST",
    recipient: str | None = "Acme Demo Inc.",
    department: str | None = "Ingenieria",
    jev: list[JevSignal] | None = None,
    ledger: tuple[LedgerEntry, ...] = (),
    received_at: datetime | None = None,
    contract_confirmed: bool = True,
    fee_amount: float = 800.0,
    fee_currency: str = "USD",
) -> RuleContext:
    from datetime import date

    due = date.fromisoformat(due_date) if due_date else None
    extraction = Extraction(
        beneficiary=beneficiary,
        amount=amount,
        currency=currency,
        amount_base=amount_base,
        due_date=due,
        invoice_number=invoice_number,
        recipient=recipient,
        department=department,
        invoice_type="servicios",
    )
    terms = ContractTerms(beneficiary=beneficiary, fee_amount=fee_amount, fee_currency=fee_currency)
    return RuleContext(
        rules=rules,
        fx_table=fx_table,
        extraction=extraction,
        contract_terms=terms,
        contract_confirmed=contract_confirmed,
        jev_signals=jev if jev is not None else _signals("J1", "J2", "J3", "J4", "J7"),
        ledger=ledger,
        received_at=received_at or datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
    )


def test_entries_before_tie_breaks_on_invoice_id() -> None:
    stamp = datetime(2026, 5, 10, 10, 0, tzinfo=UTC)
    entry_a = LedgerEntry(
        beneficiary="A",
        amount_base=1.0,
        currency="USD",
        invoice_number="NUM-A",
        received_at="2026-05-10T10:00:00Z",
        decision="PAGAR",
    )
    entry_b = LedgerEntry(
        beneficiary="B",
        amount_base=2.0,
        currency="USD",
        invoice_number="NUM-B",
        received_at="2026-05-10T10:00:00Z",
        decision="PAGAR",
    )
    ledger = (
        Ledger.empty()
        .record_settlement(entry_a, invoice_id="aaa")
        .record_settlement(entry_b, invoice_id="bbb")
    )
    before_bbb = ledger.entries_before(stamp, "bbb")
    before_aaa = ledger.entries_before(stamp, "aaa")
    assert len(before_bbb) == 1
    assert before_bbb[0].beneficiary == "A"
    assert before_aaa == ()


def test_from_seed_dev024_may_total_is_19300() -> None:
    catalog = _load_catalog()
    row = _catalog_by_id(catalog, "dev-024")
    ledger = Ledger.from_seed(row["ledger_seed"])
    assert period_paid_total(ledger.as_tuple(), 2026, 5) == 19300.0


def test_escalar_seed_does_not_increase_period_total() -> None:
    rows = [
        {
            "beneficiary": "X",
            "amount_base": 10000,
            "currency": "USD",
            "invoice_number": "S1",
            "received_at": "2026-05-02T10:00:00Z",
            "decision": "PAGAR",
        },
        {
            "beneficiary": "X",
            "amount_base": 9999,
            "currency": "USD",
            "invoice_number": "S2",
            "received_at": "2026-05-03T10:00:00Z",
            "decision": "ESCALAR",
        },
    ]
    ledger = Ledger.from_seed(rows)
    assert period_paid_total(ledger.as_tuple(), 2026, 5) == 10000.0
    assert len(ledger.as_tuple()) == 1


def test_dup_sequence_dev012_then_dev013() -> None:
    catalog = _load_catalog()
    row_012 = _catalog_by_id(catalog, "dev-012")
    row_013 = _catalog_by_id(catalog, "dev-013")
    prior = Ledger.empty()
    view_012 = ledger_view_for_invoice(row_012, prior)
    received_012 = datetime.fromisoformat(row_012["received_at"].replace("Z", "+00:00"))
    norm = normalize_beneficiary(row_012["beneficiary"])
    assert (
        duplicate_match(
            view_012,
            norm,
            row_012["invoice_number"],
            float(row_012["amount"]),
            normalize_currency(row_012["currency"]),
            received_012,
        )
        is None
    )
    entry_012 = LedgerEntry(
        beneficiary=row_012["beneficiary"],
        amount_base=float(row_012["amount"]),
        currency=row_012["currency"],
        invoice_number=row_012["invoice_number"],
        received_at=row_012["received_at"],
        decision="PAGAR",
        department=row_012.get("department"),
    )
    settled = prior.record_settlement(entry_012, invoice_id="dev-012")
    view_013 = ledger_view_for_invoice(row_013, settled)
    received_013 = datetime.fromisoformat(row_013["received_at"].replace("Z", "+00:00"))
    assert (
        duplicate_match(
            view_013,
            normalize_beneficiary(row_013["beneficiary"]),
            row_013["invoice_number"],
            float(row_013["amount"]),
            normalize_currency(row_013["currency"]),
            received_013,
        )
        == "exact"
    )


def test_dev026_marketing_spent_is_1500() -> None:
    catalog = _load_catalog()
    row = _catalog_by_id(catalog, "dev-026")
    seed_rows = []
    for seed in row["ledger_seed"]:
        copy = dict(seed)
        copy["department"] = "Marketing"
        seed_rows.append(copy)
    ledger = Ledger.from_seed(seed_rows)
    assert department_spent(ledger.as_tuple(), "Marketing") == 1500.0


def test_catalog_dev025_seed_plus_amount_exceeds_20000() -> None:
    catalog = _load_catalog()
    row = _catalog_by_id(catalog, "dev-025")
    ledger = Ledger.from_seed(row["ledger_seed"])
    august_total = period_paid_total(ledger.as_tuple(), 2026, 8)
    assert august_total == 19500.0
    assert august_total + float(row["amount"]) > 20000.0


def test_record_settlement_ignores_frenar_and_does_not_mutate() -> None:
    ledger = Ledger.empty()
    frenar = LedgerEntry(
        beneficiary="X",
        amount_base=100.0,
        currency="USD",
        invoice_number="F1",
        received_at="2026-05-01T10:00:00Z",
        decision="FRENAR",
    )
    after_frenar = ledger.record_settlement(frenar, invoice_id="inv-f")
    assert after_frenar is ledger
    assert after_frenar.as_tuple() == ()
    pagar = LedgerEntry(
        beneficiary="Y",
        amount_base=200.0,
        currency="USD",
        invoice_number="P1",
        received_at="2026-05-02T10:00:00Z",
        decision="PAGAR",
    )
    after_pagar = ledger.record_settlement(pagar, invoice_id="inv-p")
    assert after_pagar is not ledger
    assert ledger.as_tuple() == ()
    assert len(after_pagar.as_tuple()) == 1


def test_r05_ok_on_empty_dev012_view(rules: RulesConfig, fx_table: FxTable) -> None:
    from app.rules.checks import check_r05

    catalog = _load_catalog()
    row = _catalog_by_id(catalog, "dev-012")
    view = ledger_view_for_invoice(row, Ledger.empty())
    received = datetime.fromisoformat(row["received_at"].replace("Z", "+00:00"))
    ctx = make_context(
        rules,
        fx_table,
        beneficiary=row["beneficiary"],
        amount=float(row["amount"]),
        currency=row["currency"],
        amount_base=float(row["amount"]),
        invoice_number=row["invoice_number"],
        department=row.get("department"),
        ledger=view,
        received_at=received,
    )
    assert check_r05(ctx).result == "OK"
