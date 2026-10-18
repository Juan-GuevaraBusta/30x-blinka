"""T2.6 — Decision record templates and builder (docs/04 §5–§6)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from app.gate.invariants import explanation_covers_failed_checks
from app.models.domain import CheckResult, Extraction
from app.models.rules_config import RulesConfig, load_rules_config
from app.records.build import (
    RecordContext,
    build_admin_notice,
    build_next_step,
    build_summary,
    enrich_check_details,
)
from app.rules.context import ContractTerms, LedgerEntry, RuleContext
from app.rules.decide import decide
from app.rules.fx import FxTable, load_fx_table
from app.rules.run_checks import run_deterministic_checks

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def rules() -> RulesConfig:
    return load_rules_config(REPO_ROOT / "data" / "rules.json")


@pytest.fixture(scope="module")
def fx_table() -> FxTable:
    return load_fx_table(REPO_ROOT / "data" / "fx.json")


def _signals():
    from app.models.domain import JevSignal

    return [
        JevSignal(id=jid, answer=True, probability=0.99)  # type: ignore[arg-type]
        for jid in ("J1", "J2", "J3", "J4", "J7")
    ]


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
    ledger: tuple[LedgerEntry, ...] = (),
    received_at: datetime | None = None,
    contract_confirmed: bool = True,
    fee_amount: float = 800.0,
    fee_currency: str = "USD",
    manual_block: bool = False,
) -> RuleContext:
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
        jev_signals=_signals(),
        doc_text="",
        ledger=ledger,
        received_at=received_at or datetime(2026, 5, 13, 10, 0, tzinfo=UTC),
        manual_block=manual_block,
    )


def _record_ctx(rule_ctx: RuleContext, invoice_id: str = "INV-TEST-001") -> RecordContext:
    return RecordContext.from_rule_context(rule_ctx, invoice_id=invoice_id)


def _seed(
    beneficiary="Globex LLC",
    amount_base=800.0,
    currency="USD",
    number="SEED-A",
    received="2026-08-21T10:00:00Z",
    decision="PAGAR",
    department=None,
) -> LedgerEntry:
    return LedgerEntry(
        beneficiary=beneficiary,
        amount_base=amount_base,
        currency=currency,
        invoice_number=number,
        received_at=received,
        decision=decision,
        department=department,
    )


def test_pagar_summary_thirteen_ok_checks(rules, fx_table) -> None:
    ctx = make_context(rules, fx_table)
    checks = run_deterministic_checks(ctx)
    assert len(checks) == 13
    assert all(c.result == "OK" for c in checks)
    decision = decide(checks)
    assert decision == "PAGAR"
    rctx = _record_ctx(ctx)
    summary = build_summary(decision, checks, rctx)
    assert summary == (
        "Pagada: cumple todas las reglas (13 chequeos). "
        "Monto USD 800, vence 2026-05-27."
    )
    assert explanation_covers_failed_checks(summary, checks)


def test_r01_frenar_summary_and_admin_notice(rules, fx_table) -> None:
    ctx = make_context(rules, fx_table, beneficiary="Nuevo Socio Fantasma SAS")
    checks = run_deterministic_checks(ctx)
    decision = decide(checks)
    assert decision == "FRENAR"
    rctx = _record_ctx(ctx, invoice_id="INV-R01")
    summary = build_summary(decision, checks, rctx)
    assert "R01" in summary
    assert (
        summary
        == "Frenada: Nuevo Socio Fantasma SAS no está en la lista de beneficiarios "
        "permitidos (regla R01)."
    )
    notice = build_admin_notice(decision, checks, rctx, summary)
    assert notice is not None
    assert "INV-R01" in notice
    assert "Nuevo Socio Fantasma SAS" in notice
    assert "R01" in notice
    assert explanation_covers_failed_checks(summary, checks)


def test_r02_escalar_summary_includes_limit(rules, fx_table) -> None:
    ctx = make_context(
        rules,
        fx_table,
        amount=6000.0,
        amount_base=6000.0,
        fee_amount=6000.0,
    )
    checks = run_deterministic_checks(ctx)
    decision = decide(checks)
    assert decision == "ESCALAR"
    rctx = _record_ctx(ctx)
    summary = build_summary(decision, checks, rctx)
    assert "R02" in summary
    assert "5000" in summary
    assert "6000" in summary
    assert explanation_covers_failed_checks(summary, checks)


def test_r03_escalar_summary_with_period_accumulated(rules, fx_table) -> None:
    ledger = (
        _seed(
            beneficiary="Cargo Periodo Sintetico SA",
            amount_base=10000.0,
            number="SEED-A",
            received="2026-05-02T10:00:00Z",
        ),
        _seed(
            beneficiary="Cargo Periodo Sintetico SA",
            amount_base=9300.0,
            number="SEED-B",
            received="2026-05-10T10:00:00Z",
        ),
    )
    ctx = make_context(rules, fx_table, ledger=ledger)
    checks = run_deterministic_checks(ctx)
    decision = decide(checks)
    rctx = _record_ctx(ctx)
    summary = build_summary(decision, checks, rctx)
    assert summary == (
        "Escalada: con este pago el acumulado del mes sería USD 20100, "
        "sobre el límite de USD 20000 (regla R03)."
    )
    assert explanation_covers_failed_checks(summary, checks)


def test_r04_escalar_summary_at_threshold(rules, fx_table) -> None:
    ctx = make_context(
        rules,
        fx_table,
        amount=4200.0,
        amount_base=4200.0,
        fee_amount=4200.0,
    )
    checks = run_deterministic_checks(ctx)
    decision = decide(checks)
    rctx = _record_ctx(ctx)
    summary = build_summary(decision, checks, rctx)
    assert summary == (
        "Escalada: USD 4200 llega al umbral de aprobación humana de USD 3000 (regla R04)."
    )
    assert explanation_covers_failed_checks(summary, checks)


def test_r05_exact_frenar_summary(rules, fx_table) -> None:
    ledger = (
        _seed(
            beneficiary="Globex LLC",
            number="INV-GX-DUP-EXACT",
            received="2026-08-21T10:00:00Z",
        ),
    )
    ctx = make_context(
        rules,
        fx_table,
        invoice_number="INV-GX-DUP-EXACT",
        received_at=datetime(2026, 8, 23, 10, 0, tzinfo=UTC),
        ledger=ledger,
    )
    checks = run_deterministic_checks(ctx)
    decision = decide(checks)
    assert decision == "FRENAR"
    rctx = _record_ctx(ctx)
    summary = build_summary(decision, checks, rctx)
    assert summary == (
        "Frenada: ya existe una factura INV-GX-DUP-EXACT de Globex LLC "
        "registrada el 2026-08-21 (regla R05)."
    )
    assert explanation_covers_failed_checks(summary, checks)


def test_r07_frenar_budget_remaining(rules, fx_table) -> None:
    ledger = (
        _seed(
            beneficiary="Norteclaro SpA",
            amount_base=1500.0,
            number="SEED-R07",
            department="Marketing",
            received="2026-05-01T10:00:00Z",
        ),
    )
    ctx = make_context(
        rules,
        fx_table,
        department="Marketing",
        amount=4200.0,
        amount_base=4200.0,
        fee_amount=4200.0,
        ledger=ledger,
    )
    checks = run_deterministic_checks(ctx)
    decision = decide(checks)
    assert decision == "FRENAR"
    rctx = _record_ctx(ctx)
    summary = build_summary(decision, checks, rctx)
    assert "R07" in summary
    assert "3500" in summary
    assert "4200" in summary
    assert "Marketing" in summary
    assert explanation_covers_failed_checks(summary, checks)


def test_multiple_failures_summary_cites_each_rule(rules, fx_table) -> None:
    """Synthetic checks: gate requires every non-OK rule code in summary."""
    checks = [
        CheckResult(
            rule="R01",
            name="Beneficiario permitido",
            result="FALLA",
            detail="x",
            on_fail="FRENAR",
        ),
        CheckResult(
            rule="R02",
            name="Límite por pago",
            result="FALLA",
            detail="x",
            on_fail="ESCALAR",
        ),
    ]
    ctx = make_context(rules, fx_table, amount=6000.0, amount_base=6000.0)
    decision = decide(checks)
    assert decision == "FRENAR"
    rctx = _record_ctx(ctx)
    summary = build_summary(decision, checks, rctx)
    assert "R01" in summary
    assert "R02" in summary
    assert explanation_covers_failed_checks(summary, checks)


def test_enrich_check_details_uses_templates_for_failures(rules, fx_table) -> None:
    ctx = make_context(
        rules, fx_table, amount=4200.0, amount_base=4200.0, fee_amount=4200.0
    )
    checks = run_deterministic_checks(ctx)
    rctx = _record_ctx(ctx)
    enriched = enrich_check_details(checks, rctx)
    r04 = next(c for c in enriched if c.rule == "R04")
    assert r04.result == "FALLA"
    assert "3000" in r04.detail
    assert "R04" in r04.detail


def test_next_step_escalar_r04_uses_approver(rules, fx_table) -> None:
    ctx = make_context(
        rules, fx_table, amount=4200.0, amount_base=4200.0, department="Ingenieria"
    )
    checks = run_deterministic_checks(ctx)
    decision = decide(checks)
    rctx = _record_ctx(ctx)
    step = build_next_step(decision, checks, rctx)
    assert step == "Pendiente de aprobación de finanzas@demo.test."


def test_next_step_pagar(rules, fx_table) -> None:
    ctx = make_context(rules, fx_table)
    checks = run_deterministic_checks(ctx)
    decision = decide(checks)
    rctx = _record_ctx(ctx)
    assert build_next_step(decision, checks, rctx) == "Pago simulado registrado."


# --- T7.1 (D059) §3 — R14 uses its own template, not the generic INDETERMINADO one -


def test_enrich_check_details_uses_r14_template_for_route_failure(rules, fx_table) -> None:
    from app.models.rules_config import ApprovalPolicy

    policy = ApprovalPolicy.model_validate(
        {
            "routes": [
                {
                    "id": "alto-monto",
                    "match": {"amount_base_gte": 3000},
                    "require": {
                        "mode": "approvals",
                        "min_approvals": 2,
                        "from_groups": ["finanzas", "cfo"],
                    },
                },
                {"id": "default", "match": {}, "require": {"mode": "auto"}},
            ]
        }
    )
    policy_rules = rules.model_copy(update={"approval_policy": policy})
    ctx = make_context(
        policy_rules, fx_table, amount=4200.0, amount_base=4200.0, fee_amount=4200.0
    )
    checks = run_deterministic_checks(ctx)
    rctx = _record_ctx(ctx)
    enriched = enrich_check_details(checks, rctx)
    r14 = next(c for c in enriched if c.rule == "R14")
    assert r14.result == "FALLA"
    assert r14.detail == (
        "Escalada: la política de la empresa (ruta alto-monto) exige 2 "
        "aprobaciones de cfo o finanzas (regla R14)."
    )
    assert "no se pudo completar" not in r14.detail

    decision = decide(checks)
    summary = build_summary(decision, checks, rctx)
    assert "R14" in summary
    assert explanation_covers_failed_checks(summary, checks)


# --- T7.2 (D059) §3 — R16 uses its own template (serie, periodo, numero) ------------


def test_enrich_check_details_uses_r16_template_for_duplicate_period(
    rules, fx_table
) -> None:
    from app.models.rules_config import PaymentSeries
    from app.rules.context import LedgerEntry

    series = PaymentSeries.model_validate(
        {
            "id": "cuotasur-cuotas",
            "beneficiary": "Globex LLC",
            "periodicity": "installments",
            "currency": "USD",
            "total_cap": 2000,
            "items": [
                {"key": "1/3", "due_from": "2026-02-01", "due_to": "2026-02-28", "amount": 1000},
                {"key": "2/3", "due_from": "2026-03-01", "due_to": "2026-03-31", "amount": 1000},
            ],
        }
    )
    policy_rules = rules.model_copy(update={"payment_series": [series]})
    seed = LedgerEntry(
        beneficiary="Globex LLC",
        amount_base=1000.0,
        currency="USD",
        invoice_number="INV-SEED-2",
        received_at="2026-03-01T09:00:00Z",
        decision="PAGAR",
        department="Ingenieria",
        due_date="2026-03-05",
    )
    ctx = make_context(
        policy_rules,
        fx_table,
        amount=1000.0,
        amount_base=1000.0,
        fee_amount=1000.0,
        invoice_number="INV-NEW",
        due_date="2026-03-10",
        ledger=(seed,),
    )
    checks = run_deterministic_checks(ctx)
    rctx = _record_ctx(ctx)
    enriched = enrich_check_details(checks, rctx)
    r16 = next(c for c in enriched if c.rule == "R16")
    assert r16.result == "FALLA"
    assert r16.detail == (
        "Frenada: el periodo 2/3 de la serie cuotasur-cuotas ya se pagó con la "
        "factura INV-SEED-2 (regla R16)."
    )

    decision = decide(checks)
    summary = build_summary(decision, checks, rctx)
    assert "R16" in summary
    assert explanation_covers_failed_checks(summary, checks)


# --- T7.2 (D059) follow-up — R15 explains the pactated window vs the invoice date --


def test_enrich_check_details_r15_template_states_window_and_invoice_date(
    rules, fx_table
) -> None:
    from app.models.rules_config import PaymentSeries

    series = PaymentSeries.model_validate(
        {
            "id": "globex-retainer",
            "beneficiary": "Globex LLC",
            "department": "Ingenieria",
            "periodicity": "monthly",
            "currency": "USD",
            "expected_amount": {"min": 800, "max": 800},
            "start": "2026-01-01",
            "end": "2026-03-31",
        }
    )
    policy_rules = rules.model_copy(update={"payment_series": [series]})
    ctx = make_context(
        policy_rules,
        fx_table,
        amount=800.0,
        amount_base=800.0,
        fee_amount=800.0,
        due_date="2026-04-15",
    )
    checks = run_deterministic_checks(ctx)
    rctx = _record_ctx(ctx)
    enriched = enrich_check_details(checks, rctx)
    r15 = next(c for c in enriched if c.rule == "R15")
    assert r15.result == "FALLA"
    assert r15.detail == (
        "Escalada: la fecha de la factura (2026-04-15) no cumple la serie pactada "
        "globex-retainer (vigencia pactada del 2026-01-01 al 2026-03-31) (regla R15)."
    )

    decision = decide(checks)
    summary = build_summary(decision, checks, rctx)
    assert "R15" in summary
    assert explanation_covers_failed_checks(summary, checks)


def test_enrich_check_details_r17_acumulado_excludes_reprocessed_invoice(
    rules, fx_table
) -> None:
    """The R17 explanation's "acumulado" must match what the check itself used
    (excluding a reprocessed invoice), not a stale double-counted total."""
    from app.models.rules_config import PaymentSeries
    from app.rules.context import LedgerEntry

    series = PaymentSeries.model_validate(
        {
            "id": "cuotasur-cuotas",
            "beneficiary": "Globex LLC",
            "periodicity": "installments",
            "currency": "USD",
            "total_cap": 2000,
            "items": [
                {"key": "1/3", "due_from": "2026-02-01", "due_to": "2026-02-28", "amount": 1000},
                {"key": "2/3", "due_from": "2026-03-01", "due_to": "2026-03-31", "amount": 1000},
            ],
        }
    )
    policy_rules = rules.model_copy(update={"payment_series": [series]})
    seed = LedgerEntry(
        beneficiary="Globex LLC",
        amount_base=1500.0,
        currency="USD",
        invoice_number="INV-REPROCESS",
        received_at="2026-02-01T09:00:00Z",
        decision="PAGAR",
        department="Ingenieria",
        due_date="2026-02-05",
    )
    ctx = make_context(
        policy_rules,
        fx_table,
        amount=2500.0,
        amount_base=2500.0,
        fee_amount=2500.0,
        invoice_number="INV-REPROCESS",
        due_date="2026-02-10",
        ledger=(seed,),
    )
    checks = run_deterministic_checks(ctx)
    rctx = _record_ctx(ctx)
    enriched = enrich_check_details(checks, rctx)
    r17 = next(c for c in enriched if c.rule == "R17")
    assert r17.result == "FALLA"
    assert "USD 0" in r17.detail
    assert "USD 1500" not in r17.detail
