"""Pure builders for DecisionRecord explanations (docs/04 §5–§6). No LLM."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.models.domain import CheckResult, Decision, Extraction
from app.models.rules_config import PaymentSeries, RulesConfig
from app.records import templates as tpl
from app.rules.approval_policy import parse_r14_quote
from app.rules.context import ContractTerms, LedgerEntry, RuleContext
from app.rules.ledger_queries import (
    department_spent_for_budget,
    duplicate_match,
    period_paid_total,
)
from app.rules.normalize import (
    normalize_beneficiary,
    normalize_currency,
    normalize_invoice_number,
)
from app.rules.payment_series import (
    find_matching_series,
    first_period_conflict,
    paid_total_for_series,
    period_key,
)

_RULE_NAMES: dict[str, str] = {
    "R01": "Beneficiario permitido",
    "R02": "Límite por pago",
    "R03": "Límite por periodo",
    "R04": "Aprobación humana por monto",
    "R05": "Duplicado",
    "R06": "Cuadra con contrato",
    "R07": "Presupuesto del departamento",
    "R08": "Destinatario es la empresa",
    "R09": "Extracción fiable",
    "R10": "Moneda convertible",
    "R11": "Fecha de pago definida",
    "R12": "Bloqueo manual",
    "R13": "Sin instrucciones embebidas",
    "R14": "Política de aprobación",
    "R15": "Dentro de la serie pactada",
    "R16": "Periodo ya pagado",
    "R17": "Total de la serie",
    "R18": "Periodo esperado sin factura",
    "R19": "Cuadra con la fórmula pactada",
    "R20": "Primer pago de proveedor nuevo",
    "R21": "Fraccionamiento",
}


def _fmt_usd(amount: float) -> str:
    if amount == int(amount):
        return str(int(amount))
    return f"{amount:g}"


def _fmt_date(value: date | None) -> str:
    return value.isoformat() if value is not None else "s/f"


@dataclass(frozen=True)
class RecordContext:
    """Inputs for template placeholders beyond raw CheckResult rows."""

    rules: RulesConfig
    extraction: Extraction
    ledger: tuple[LedgerEntry, ...] = ()
    received_at: datetime | None = None
    invoice_id: str = ""
    contract_terms: ContractTerms | None = None
    contract_confirmed: bool = True

    @classmethod
    def from_rule_context(cls, ctx: RuleContext, *, invoice_id: str) -> RecordContext:
        return cls(
            rules=ctx.rules,
            extraction=ctx.extraction,
            ledger=ctx.ledger,
            received_at=ctx.received_at,
            invoice_id=invoice_id,
            contract_terms=ctx.contract_terms,
            contract_confirmed=ctx.contract_confirmed,
        )


def _amount_base(ctx: RecordContext) -> float | None:
    if ctx.extraction.amount_base is not None:
        return float(ctx.extraction.amount_base)
    return None


def _exact_duplicate_registration_date(ctx: RecordContext) -> date | None:
    norm = normalize_beneficiary(ctx.extraction.beneficiary)
    number = normalize_invoice_number(ctx.extraction.invoice_number)
    if norm is None or number is None:
        return None
    for entry in ctx.ledger:
        if (
            normalize_beneficiary(entry.beneficiary) == norm
            and normalize_invoice_number(entry.invoice_number) == number
        ):
            try:
                stamp = datetime.fromisoformat(entry.received_at.replace("Z", "+00:00"))
            except ValueError:
                return None
            return stamp.date()
    return None


def _r15_window_text(series: PaymentSeries) -> str:
    """Plain-Spanish description of the series' expected window (T7.2 follow-up).

    Used by the R15 explanation so it states what was pactated, not just
    that something failed.
    """
    if series.periodicity in ("installments", "milestones"):
        windows = "; ".join(
            f"{item.key} ({item.due_from.isoformat()} a {item.due_to.isoformat()})"
            for item in series.items
        )
        return f"ítems pactados: {windows}"
    start_text = series.start.isoformat() if series.start is not None else "sin fecha de inicio"
    end_text = series.end.isoformat() if series.end is not None else "sin fecha de fin"
    return f"vigencia pactada del {start_text} al {end_text}"


def _r05_is_probable(check: CheckResult) -> bool:
    return check.rule == "R05" and "Posible duplicado" in check.detail


def _summary_line_for_check(check: CheckResult, ctx: RecordContext) -> str:
    rule = check.rule
    amount = _amount_base(ctx)
    monto = _fmt_usd(amount) if amount is not None else "s/m"

    if check.result == "OK":
        return ""

    if check.result == "INDETERMINADO":
        return tpl.TEMPLATE_RULE_INDETERMINATE.format(
            nombre=_RULE_NAMES.get(rule, rule),
            motivo=check.detail.rstrip("."),
            rule=rule,
        )

    if rule == "R01":
        ben = ctx.extraction.beneficiary or "s/b"
        return tpl.TEMPLATE_R01_FAIL.format(beneficiario=ben)

    if rule == "R02" and amount is not None and amount <= 0:
        return tpl.TEMPLATE_R02_NONPOSITIVE_FAIL.format(monto_base=monto)

    if rule == "R02" and amount is not None:
        return tpl.TEMPLATE_R02_FAIL.format(
            monto_base=monto,
            limite=_fmt_usd(float(ctx.rules.limits.per_payment)),
        )

    if rule == "R03" and amount is not None and ctx.received_at is not None:
        total = period_paid_total(
            ctx.ledger, ctx.received_at.year, ctx.received_at.month
        )
        acum = (total or 0.0) + amount
        return tpl.TEMPLATE_R03_FAIL.format(
            acum=_fmt_usd(acum),
            limite=_fmt_usd(float(ctx.rules.limits.per_period.amount)),
        )

    if rule == "R04" and amount is not None:
        return tpl.TEMPLATE_R04_FAIL.format(
            monto_base=monto,
            umbral=_fmt_usd(float(ctx.rules.human_approval_threshold)),
        )

    if rule == "R05":
        if _r05_is_probable(check):
            return tpl.TEMPLATE_R05_PROBABLE_FAIL
        reg_date = _exact_duplicate_registration_date(ctx)
        return tpl.TEMPLATE_R05_EXACT_FAIL.format(
            numero=ctx.extraction.invoice_number or "s/n",
            beneficiario=ctx.extraction.beneficiary or "s/b",
            fecha=_fmt_date(reg_date),
        )

    if rule == "R06" and amount is not None:
        clause = "s/c"
        pactado = "s/p"
        if check.evidence and check.evidence.clause:
            clause = check.evidence.clause
        if ctx.contract_terms is not None:
            pactado = (
                f"USD {_fmt_usd(ctx.contract_terms.fee_amount)}"
                if normalize_currency(ctx.contract_terms.fee_currency) == "USD"
                else f"{ctx.contract_terms.fee_amount:g} {ctx.contract_terms.fee_currency}"
            )
        cobrado = f"USD {monto}"
        return tpl.TEMPLATE_R06_FAIL.format(
            clausula=clause, pactado=pactado, cobrado=cobrado
        )

    if rule == "R07" and amount is not None:
        depto = ctx.extraction.department or "s/d"
        budget = ctx.rules.department_budgets.get(depto)
        spent = (
            department_spent_for_budget(ctx.ledger, depto, ctx.received_at)
            if depto != "s/d"
            else 0.0
        )
        saldo = (budget - spent) if budget is not None and spent is not None else 0.0
        return tpl.TEMPLATE_R07_FAIL.format(
            depto=depto,
            saldo=_fmt_usd(saldo),
            monto_base=monto,
        )

    if rule == "R14":
        route_id = check.evidence.clause if check.evidence else "s/r"
        parsed = parse_r14_quote(check.evidence.quote if check.evidence else None)
        if parsed is None:
            return tpl.TEMPLATE_RULE_INDETERMINATE.format(
                nombre=_RULE_NAMES.get(rule, rule),
                motivo="evidencia de la política ilegible",
                rule=rule,
            )
        min_approvals, groups = parsed
        return tpl.TEMPLATE_R14_FAIL.format(
            ruta=route_id, n=min_approvals, grupos=" o ".join(groups)
        )

    if rule in ("R15", "R16", "R17") and ctx.rules.payment_series:
        resolution = find_matching_series(ctx.rules.payment_series, ctx.extraction)
        serie_id = resolution.series.id if resolution.series is not None else "s/serie"

        if rule == "R15":
            fecha = _fmt_date(ctx.extraction.due_date)
            ventana = (
                _r15_window_text(resolution.series)
                if resolution.series is not None
                else "s/ventana"
            )
            return tpl.TEMPLATE_R15_FAIL.format(serie=serie_id, fecha=fecha, ventana=ventana)

        if rule == "R16":
            periodo = "s/p"
            numero = "s/n"
            if resolution.series is not None and ctx.extraction.due_date is not None:
                periodo = period_key(resolution.series, ctx.extraction.due_date) or "s/p"
                conflict = first_period_conflict(
                    ctx.ledger,
                    resolution.series,
                    ctx.extraction.due_date,
                    ctx.extraction.invoice_number,
                )
                if conflict is not None:
                    numero = conflict.invoice_number
            return tpl.TEMPLATE_R16_FAIL.format(periodo=periodo, serie=serie_id, numero=numero)

        # rule == "R17"
        acumulado = "0"
        tope = "s/t"
        if resolution.series is not None:
            paid_total = paid_total_for_series(
                ctx.ledger,
                resolution.series,
                exclude_invoice_number=ctx.extraction.invoice_number,
            )
            acumulado = _fmt_usd(paid_total) if paid_total is not None else "s/m"
            if resolution.series.total_cap is not None:
                tope = _fmt_usd(float(resolution.series.total_cap))
        return tpl.TEMPLATE_R17_FAIL.format(serie=serie_id, acumulado=acumulado, tope=tope)

    if rule == "R11":
        # T5.13 (D063): R11 only FALLA for an implausible due date (missing = INDETERMINADO).
        return tpl.TEMPLATE_R11_RANGE_FAIL.format(fecha=_fmt_date(ctx.extraction.due_date))

    if rule == "R21":
        return tpl.TEMPLATE_R21_FAIL.format(
            beneficiario=ctx.extraction.beneficiary or "s/b",
            dias=ctx.rules.splitting_window_days,
            umbral=_fmt_usd(float(ctx.rules.human_approval_threshold)),
        )

    fallbacks = {
        "R08": tpl.TEMPLATE_R08_FAIL,
        "R09": tpl.TEMPLATE_R09_FAIL,
        "R10": tpl.TEMPLATE_R10_FAIL,
        "R11": tpl.TEMPLATE_R11_FAIL,
        "R12": tpl.TEMPLATE_R12_FAIL,
        "R13": tpl.TEMPLATE_R13_FAIL,
    }
    if rule in fallbacks:
        return fallbacks[rule]

    return tpl.TEMPLATE_RULE_INDETERMINATE.format(
        nombre=_RULE_NAMES.get(rule, rule),
        motivo=check.detail.rstrip("."),
        rule=rule,
    )


def build_summary(decision: Decision, checks: list[CheckResult], ctx: RecordContext) -> str:
    """Summary text aligned with decide() and §6 templates."""
    if decision == "PAGAR" and all(c.result == "OK" for c in checks):
        amount = _amount_base(ctx)
        monto = _fmt_usd(amount) if amount is not None else "s/m"
        return tpl.TEMPLATE_PAGAR.format(
            n=len(checks),
            monto_base=monto,
            fecha=_fmt_date(ctx.extraction.due_date),
        )

    parts: list[str] = []
    for check in checks:
        if check.result == "OK":
            continue
        line = _summary_line_for_check(check, ctx)
        if line:
            parts.append(line)
    if not parts:
        return tpl.TEMPLATE_TECHNICAL_ERROR.format(motivo="sin chequeos fallidos identificados")
    return " ".join(parts)


def format_check_detail(check: CheckResult, ctx: RecordContext) -> str:
    """Template-backed detail for a single check (builder source of truth for UI/eval)."""
    if check.result == "OK":
        return check.detail
    line = _summary_line_for_check(check, ctx)
    return line if line else check.detail


def enrich_check_details(
    checks: list[CheckResult], ctx: RecordContext
) -> list[CheckResult]:
    return [
        check.model_copy(update={"detail": format_check_detail(check, ctx)})
        for check in checks
    ]


def _primary_frenar_motivo(checks: list[CheckResult], ctx: RecordContext) -> str:
    for check in checks:
        if check.result != "OK" and check.on_fail == "FRENAR":
            line = _summary_line_for_check(check, ctx)
            if line.startswith("Frenada:"):
                return line.removeprefix("Frenada:").strip()
            if line.startswith("Frenada por el verificador:"):
                return line.removeprefix("Frenada por el verificador:").strip()
    for check in checks:
        if check.result != "OK":
            line = _summary_line_for_check(check, ctx)
            return line.split("(regla")[0].strip()
    return "violación de reglas de pago"


def _evidence_for_admin(checks: list[CheckResult]) -> str:
    for check in checks:
        if check.result != "OK" and check.on_fail == "FRENAR":
            if check.evidence and check.evidence.clause:
                return f"cláusula {check.evidence.clause}"
            return f"regla {check.rule}"
    for check in checks:
        if check.result != "OK":
            return f"regla {check.rule}"
    return "reglas de pago"


def build_admin_notice(
    decision: Decision,
    checks: list[CheckResult],
    ctx: RecordContext,
    summary: str | None = None,
) -> str | None:
    if decision != "FRENAR":
        return None
    motivo = _primary_frenar_motivo(checks, ctx)
    if summary and "verificador" in summary.lower():
        motivo = summary.split("Se notificó")[0].replace("Frenada por el verificador:", "").strip()
    return tpl.TEMPLATE_ADMIN_NOTICE.format(
        id=ctx.invoice_id or "s/id",
        beneficiario=ctx.extraction.beneficiary or "s/b",
        motivo=motivo.rstrip("."),
        cita_o_regla=_evidence_for_admin(checks),
    )


def _needs_human_approval(checks: list[CheckResult]) -> bool:
    return any(
        c.rule == "R04" and c.result != "OK"
        for c in checks
    )


def _approver_email(ctx: RecordContext) -> str:
    dept = ctx.extraction.department
    approvers = ctx.rules.approvers
    if dept and dept in approvers:
        return approvers[dept]
    return approvers.get("default", "cfo@demo.test")


def build_next_step(
    decision: Decision, checks: list[CheckResult], ctx: RecordContext
) -> str:
    if decision == "PAGAR":
        return "Pago simulado registrado."
    if decision == "FRENAR":
        return "Se notificó al administrador; no procede el pago automático."
    if _needs_human_approval(checks):
        return f"Pendiente de aprobación de {_approver_email(ctx)}."
    return "Requiere revisión humana."


def build_verifier_summary(issue: str, kind: str) -> str:
    if kind == "violation":
        return tpl.TEMPLATE_VERIFIER_VIOLATION.format(issue=issue)
    return tpl.TEMPLATE_VERIFIER_UNCERTAINTY.format(issue=issue)


def build_technical_error_summary(motivo: str) -> str:
    return tpl.TEMPLATE_TECHNICAL_ERROR.format(motivo=motivo)


def duplicate_kind(ctx: RecordContext) -> str | None:
    """Expose duplicate_match for tests and T2.8 assembly."""
    norm = normalize_beneficiary(ctx.extraction.beneficiary)
    currency = normalize_currency(ctx.extraction.currency)
    amount = _amount_base(ctx)
    return duplicate_match(
        ctx.ledger,
        norm,
        ctx.extraction.invoice_number,
        amount,
        currency,
        ctx.received_at,
    )
