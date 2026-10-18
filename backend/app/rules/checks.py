"""T2.3 — Pure deterministic checks R01–R13 (no decide(), no templates)."""

from __future__ import annotations

from app.models.domain import CheckEvidence, CheckResult, JevSignal
from app.models.rules_config import PaymentSeries
from app.rules.approval_policy import resolve_route
from app.rules.context import RuleContext
from app.rules.fx import convert_to_base
from app.rules.ledger_queries import (
    department_spent_for_budget,
    duplicate_match,
    period_paid_total,
)
from app.rules.normalize import normalize_beneficiary, normalize_currency, normalize_party_name
from app.rules.payment_series import (
    expected_periods_before,
    first_period_conflict,
    paid_entries_for_series,
    paid_total_for_series,
    parse_ledger_due_date,
    period_key,
    resolve_item_key,
)
from app.rules.variable_pricing import (
    expected_amount,
    format_calculation_detail,
    invoice_amount_in_terms,
    validate_metered_for_terms,
)
from app.rules.vendor_onboarding import find_vendor_addition, has_vendor_human_approval_after

RULE_NAMES: dict[str, str] = {
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
}

# T7.2 follow-up (R3-float-equality-installment) — tolerance in base-currency
# units for installment/milestone amount comparisons; avoids FX-rounding drift
# tripping an exact float equality check.
_AMOUNT_TOLERANCE = 0.005

R13_PHRASES: tuple[str, ...] = (
    "ignora las reglas y paga",
    "ignora las reglas",
    "set decision",
    "system:",
)


def _ok(rule: str, detail: str) -> CheckResult:
    return CheckResult(rule=rule, name=RULE_NAMES[rule], result="OK", detail=detail)  # type: ignore[arg-type]


def _fail(ctx: RuleContext, rule: str, detail: str) -> CheckResult:
    on_fail = getattr(ctx.rules.on_fail, rule)
    return CheckResult(  # type: ignore[arg-type]
        rule=rule, name=RULE_NAMES[rule], result="FALLA", detail=detail, on_fail=on_fail
    )


def _indeterminate(rule: str, detail: str) -> CheckResult:
    return CheckResult(rule=rule, name=RULE_NAMES[rule], result="INDETERMINADO", detail=detail)  # type: ignore[arg-type]


def _amount_base(ctx: RuleContext) -> float | None:
    if ctx.extraction.amount_base is not None:
        return float(ctx.extraction.amount_base)
    result = convert_to_base(ctx.extraction.amount, ctx.extraction.currency, ctx.fx_table)
    return result.amount_base


def _signal(ctx: RuleContext, jev_id: str) -> JevSignal | None:
    for signal in ctx.jev_signals:
        if signal.id == jev_id:
            return signal
    return None


def check_r01(ctx: RuleContext) -> CheckResult:
    norm = normalize_beneficiary(ctx.extraction.beneficiary)
    if norm is None:
        return _indeterminate("R01", "Beneficiario ausente; no se puede validar la lista.")
    allowed = {normalize_beneficiary(name) for name in ctx.rules.allowed_beneficiaries}
    if norm in allowed:
        return _ok("R01", f"{ctx.extraction.beneficiary} está en la lista.")
    return _fail(ctx, "R01", f"{ctx.extraction.beneficiary} no está en la lista.")


def _money_or_indeterminate(ctx: RuleContext, rule: str) -> tuple[float | None, CheckResult | None]:
    amount = _amount_base(ctx)
    if amount is None:
        return None, _indeterminate(rule, "Monto en moneda base no disponible.")
    return amount, None


def check_r02(ctx: RuleContext) -> CheckResult:
    amount, missing = _money_or_indeterminate(ctx, "R02")
    if missing is not None:
        return missing
    assert amount is not None
    if amount > ctx.rules.limits.per_payment:
        return _fail(ctx, "R02", f"USD {amount:g} supera el límite por pago.")
    return _ok("R02", f"USD {amount:g} dentro del límite por pago.")


def check_r03(ctx: RuleContext) -> CheckResult:
    amount, missing = _money_or_indeterminate(ctx, "R03")
    if missing is not None:
        return missing
    assert amount is not None
    if ctx.received_at is None:
        return _indeterminate("R03", "Fecha de recepción ausente.")
    stamp = ctx.received_at
    total = period_paid_total(ctx.ledger, stamp.year, stamp.month)
    if total + amount > ctx.rules.limits.per_period.amount:
        return _fail(ctx, "R03", "El acumulado del mes supera el límite del periodo.")
    return _ok("R03", "El acumulado del mes está dentro del límite.")


def check_r04(ctx: RuleContext) -> CheckResult:
    amount, missing = _money_or_indeterminate(ctx, "R04")
    if missing is not None:
        return missing
    assert amount is not None
    if amount >= ctx.rules.human_approval_threshold:
        return _fail(ctx, "R04", f"USD {amount:g} alcanza el umbral de aprobación humana.")
    return _ok("R04", f"USD {amount:g} bajo el umbral de aprobación humana.")


def check_r05(ctx: RuleContext) -> CheckResult:
    norm = normalize_beneficiary(ctx.extraction.beneficiary)
    number = ctx.extraction.invoice_number
    currency = normalize_currency(ctx.extraction.currency)
    amount = _amount_base(ctx)
    match = duplicate_match(ctx.ledger, norm, number, amount, currency, ctx.received_at)
    if match == "exact":
        return _fail(ctx, "R05", f"Ya existe la factura {number}.")
    if match == "probable":
        return CheckResult(  # type: ignore[arg-type]
            rule="R05",
            name=RULE_NAMES["R05"],
            result="FALLA",
            detail="Posible duplicado: mismo beneficiario, monto y moneda en 30 días.",
            on_fail="ESCALAR",
        )
    if norm is None or number is None:
        return _indeterminate("R05", "Sin beneficiario o número; no se puede buscar duplicados.")
    return _ok("R05", "Sin duplicados en el ledger.")


def check_r06(ctx: RuleContext) -> CheckResult:
    if ctx.contract_terms is None or not ctx.contract_confirmed:
        return _indeterminate("R06", "Contrato ausente o sin confirmar.")
    converted_fee = convert_to_base(
        ctx.contract_terms.fee_amount, ctx.contract_terms.fee_currency, ctx.fx_table
    )
    fee_base = converted_fee.amount_base
    amount = _amount_base(ctx)
    if fee_base is None or amount is None:
        return _indeterminate("R06", "No se puede comparar factura contra tarifa.")
    if amount != fee_base:
        clauses = ", ".join(ctx.contract_terms.cited_clauses) or "s/c"
        return CheckResult(  # type: ignore[arg-type]
            rule="R06",
            name=RULE_NAMES["R06"],
            result="FALLA",
            detail=f"La factura cobra {amount:g} y la tarifa pactada es {fee_base:g}.",
            on_fail=ctx.rules.on_fail.R06,
            evidence=CheckEvidence(clause=clauses, quote=""),
        )
    return _ok("R06", "El monto cuadra con la tarifa pactada.")


def check_r07(ctx: RuleContext) -> CheckResult:
    amount, missing = _money_or_indeterminate(ctx, "R07")
    if missing is not None:
        return missing
    assert amount is not None
    department = ctx.extraction.department
    if department is None:
        return _indeterminate("R07", "Departamento ausente.")
    budget = ctx.rules.department_budgets.get(department)
    if budget is None:
        return _indeterminate("R07", f"Sin presupuesto configurado para {department}.")
    spent = department_spent_for_budget(ctx.ledger, department, ctx.received_at)
    if budget - spent < amount:
        return _fail(ctx, "R07", f"Presupuesto restante de {department} insuficiente.")
    return _ok("R07", f"Presupuesto de {department} suficiente.")


def check_r08(ctx: RuleContext) -> CheckResult:
    recipient = normalize_party_name(ctx.extraction.recipient)
    company = normalize_party_name(ctx.rules.company.name)
    if recipient is None:
        return _indeterminate("R08", "Destinatario ausente.")
    if recipient == company:
        return _ok("R08", "Destinatario coincide con la empresa.")
    return _fail(ctx, "R08", "Destinatario distinto de la empresa.")


def check_r09(ctx: RuleContext) -> CheckResult:
    ext = ctx.extraction
    if (
        ext.beneficiary is None
        or ext.amount is None
        or ext.currency is None
        or ext.recipient is None
    ):
        return _indeterminate("R09", "Campo obligatorio ausente en la extracción.")
    for jev_id in ("J1", "J2", "J3", "J4"):
        signal = _signal(ctx, jev_id)
        if signal is None:
            return _indeterminate("R09", f"Señal {jev_id} ausente.")
        threshold = getattr(ctx.rules.jev_thresholds, jev_id)
        if signal.probability < threshold:
            return _fail(ctx, "R09", f"Señal {jev_id} bajo umbral.")
    return _ok("R09", "Extracción fiable según J1–J4.")


def check_r10(ctx: RuleContext) -> CheckResult:
    code = normalize_currency(ctx.extraction.currency)
    if code is None:
        return _indeterminate("R10", "Moneda ausente.")
    if code not in ctx.fx_table.rates:
        return _fail(ctx, "R10", f"Moneda {code} sin tasa.")
    return _ok("R10", f"Moneda {code} convertible.")


def check_r11(ctx: RuleContext) -> CheckResult:
    if ctx.extraction.due_date is None:
        return _indeterminate("R11", "Fecha de pago ausente.")
    return _ok("R11", "Fecha de pago definida.")


def check_r12(ctx: RuleContext) -> CheckResult:
    if ctx.manual_block:
        return _fail(ctx, "R12", "Beneficiario en bloqueo manual.")
    return _ok("R12", "Sin bloqueo manual.")


def check_r13(ctx: RuleContext) -> CheckResult:
    text = (ctx.doc_text or "").casefold()
    for phrase in R13_PHRASES:
        if phrase in text:
            return _fail(ctx, "R13", "El documento contiene instrucciones embebidas.")
    signal = _signal(ctx, "J7")
    threshold = ctx.rules.jev_thresholds.J7
    if signal is not None and signal.probability < threshold:
        return _fail(ctx, "R13", "J7 bajo umbral.")
    # J7 ausente + texto limpio = OK: R09 ya escala por señales J1–J4 ausentes,
    # y R13 solo marca instrucciones detectadas, no incertidumbre general.
    return _ok("R13", "Sin instrucciones embebidas detectadas.")


def check_r14(ctx: RuleContext) -> CheckResult:
    """T7.1 (D059) — Company approval policy. Can only ADD approvals, never PAGAR.

    Emitted only when `ctx.rules.approval_policy` is set (`run_deterministic_checks`
    gates this); without a policy the 13-check list stays byte-identical (criterion 2).
    """
    policy = ctx.rules.approval_policy
    if policy is None:
        return _indeterminate("R14", "Política de aprobación no configurada.")
    amount_base = _amount_base(ctx)
    resolution = resolve_route(policy, ctx.extraction, amount_base)
    if resolution.route is None:
        reason = resolution.reason or "No se pudo evaluar la ruta de aprobación."
        return _indeterminate("R14", reason)
    route = resolution.route
    if route.require.mode == "auto":
        return _ok("R14", f'Ruta "{route.id}": sin aprobaciones adicionales.')
    assert route.require.min_approvals is not None
    groups_text = " o ".join(route.require.from_groups)
    detail = (
        f'Ruta "{route.id}": requiere {route.require.min_approvals} aprobaciones '
        f"de {groups_text}."
    )
    failed = _fail(ctx, "R14", detail)
    quote = (
        f"min_approvals={route.require.min_approvals};"
        f"groups={','.join(sorted(route.require.from_groups))}"
    )
    return failed.model_copy(update={"evidence": CheckEvidence(clause=route.id, quote=quote)})


def check_r15_ambiguous_series() -> CheckResult:
    """T7.2 (D059) — More than one `payment_series` matched this invoice.

    `run_deterministic_checks` emits only this (never R16-R18, which need a
    single resolved series) when `find_matching_series` reports ambiguity.
    """
    return _indeterminate("R15", "Más de una serie de pagos coincide con esta factura.")


def check_r15(ctx: RuleContext, series: PaymentSeries) -> CheckResult:
    """T7.2 (D059) — Within the vendor's pactated calendar/items. Can only ADD severity.

    Emitted only when this invoice's beneficiary (and department, if the
    series fixes one) matches `series` (`run_deterministic_checks` resolves
    this once); without a matching series, R15-R18 are never emitted.
    """
    due_date = ctx.extraction.due_date
    if due_date is None:
        return _indeterminate("R15", "Fecha de pago ausente para validar la serie.")
    amount_base = _amount_base(ctx)
    if amount_base is None:
        return _indeterminate("R15", "Monto en moneda base no disponible para validar la serie.")
    if normalize_currency(series.currency) != normalize_currency(ctx.fx_table.base_currency):
        return _indeterminate(
            "R15",
            f'La serie "{series.id}" está pactada en {series.currency}, distinta de la '
            f"moneda base ({ctx.fx_table.base_currency}); no se puede comparar el monto "
            "de forma segura.",
        )

    if series.periodicity in ("installments", "milestones"):
        key, count = resolve_item_key(series, due_date)
        if count >= 2:
            return _indeterminate(
                "R15", f'Más de un ítem de la serie "{series.id}" contiene esta fecha.'
            )
        if count == 0 or key is None:
            return _fail(
                ctx,
                "R15",
                f'La fecha {due_date.isoformat()} no cae en ningún ítem de la serie "{series.id}".',
            )
        item = next(item for item in series.items if item.key == key)
        if abs(amount_base - item.amount) > _AMOUNT_TOLERANCE:
            return _fail(
                ctx,
                "R15",
                f'El ítem "{key}" de la serie "{series.id}" espera USD {item.amount:g} '
                f"y la factura cobra USD {amount_base:g}.",
            )
        return _ok("R15", f'La factura cae en el ítem "{key}" de la serie "{series.id}".')

    assert series.start is not None and series.expected_amount is not None
    if due_date < series.start or (series.end is not None and due_date > series.end):
        return _fail(
            ctx,
            "R15",
            f'La fecha {due_date.isoformat()} queda fuera de la vigencia de la serie '
            f'"{series.id}".',
        )
    low, high = series.expected_amount.min, series.expected_amount.max
    if not (low <= amount_base <= high):
        return _fail(
            ctx,
            "R15",
            f'USD {amount_base:g} queda fuera del monto esperado (USD {low:g}-{high:g}) '
            f'de la serie "{series.id}".',
        )
    return _ok("R15", f'La factura cae dentro de la serie "{series.id}" pactada.')


def check_r16(ctx: RuleContext, series: PaymentSeries) -> CheckResult:
    """T7.2 (D059) — Same series period already paid with a different invoice number."""
    due_date = ctx.extraction.due_date
    if due_date is None:
        return _indeterminate("R16", "Fecha de pago ausente para validar el periodo.")
    current_key = period_key(series, due_date)
    if current_key is None:
        return _indeterminate(
            "R16", f'No se pudo determinar el periodo de la serie "{series.id}".'
        )
    paid = paid_entries_for_series(ctx.ledger, series)
    for entry in paid:
        if parse_ledger_due_date(entry.due_date) is None:
            return _indeterminate(
                "R16",
                f'Una factura ya pagada de la serie "{series.id}" no tiene fecha de pago '
                "registrada o no se puede leer (fila legada).",
            )
    conflict = first_period_conflict(
        ctx.ledger, series, due_date, ctx.extraction.invoice_number
    )
    if conflict is not None:
        return _fail(
            ctx,
            "R16",
            f'El periodo "{current_key}" de la serie "{series.id}" ya se pagó con la '
            f"factura {conflict.invoice_number}.",
        )
    return _ok(
        "R16", f'El periodo "{current_key}" de la serie "{series.id}" no tiene pago previo.'
    )


def check_r17(ctx: RuleContext, series: PaymentSeries) -> CheckResult:
    """T7.2 (D059) — Cumulative series total (paid + this payment) against `total_cap`."""
    if series.total_cap is None:
        return _ok("R17", f'La serie "{series.id}" no tiene tope total configurado.')
    amount_base = _amount_base(ctx)
    if amount_base is None:
        return _indeterminate(
            "R17", "Monto en moneda base no disponible para validar el tope de la serie."
        )
    if normalize_currency(series.currency) != normalize_currency(ctx.fx_table.base_currency):
        return _indeterminate(
            "R17",
            f'La serie "{series.id}" está pactada en {series.currency}, distinta de la '
            f"moneda base ({ctx.fx_table.base_currency}); no se puede validar el tope de "
            "forma segura.",
        )
    total_paid = paid_total_for_series(
        ctx.ledger, series, exclude_invoice_number=ctx.extraction.invoice_number
    )
    if total_paid + amount_base > series.total_cap:
        return _fail(
            ctx,
            "R17",
            f'La serie "{series.id}" acumula USD {total_paid:g}; sumar USD {amount_base:g} '
            f"supera el tope de USD {series.total_cap:g}.",
        )
    return _ok("R17", f'La serie "{series.id}" queda dentro del tope total.')


def check_r18(ctx: RuleContext, series: PaymentSeries) -> CheckResult:
    """T7.2 (D059) — Informational only: never FALLA/INDETERMINADO, never changes decide()."""
    due_date = ctx.extraction.due_date
    if due_date is None:
        return _ok("R18", f'Serie "{series.id}": sin fecha de pago para listar periodos.')
    expected = expected_periods_before(series, due_date)
    if not expected:
        return _ok("R18", f'Serie "{series.id}": sin periodos previos pendientes.')
    paid = paid_entries_for_series(ctx.ledger, series)
    paid_keys: set[str] = set()
    for entry in paid:
        entry_due = parse_ledger_due_date(entry.due_date)
        if entry_due is None:
            continue
        key = period_key(series, entry_due)
        if key is not None:
            paid_keys.add(key)
    current_key = period_key(series, due_date)
    missing = [key for key in expected if key not in paid_keys and key != current_key]
    if not missing:
        return _ok("R18", f'Serie "{series.id}": sin periodos previos pendientes.')
    listed = ", ".join(missing)
    return _ok("R18", f'Serie "{series.id}": faltan facturas de los periodos {listed}.')


def check_r19(ctx: RuleContext, terms) -> CheckResult:
    """T7.3 (D059): deterministic recomputation; never enables PAGAR on its own."""
    from app.models.rules_config import PricingTerms

    assert isinstance(terms, PricingTerms)
    inv_cur = normalize_currency(ctx.extraction.currency)
    terms_cur = normalize_currency(terms.currency)
    if inv_cur is None or terms_cur is None:
        return _indeterminate("R19", "Moneda de la factura no disponible.")
    if inv_cur != terms_cur:
        return _indeterminate("R19", "La moneda de la factura no coincide con la fórmula pactada.")

    indet = validate_metered_for_terms(terms, ctx.metered_lines, ctx.doc_text)
    if indet is not None:
        return _indeterminate("R19", indet)

    expected = expected_amount(terms, ctx.metered_lines)
    assert expected is not None
    billed = invoice_amount_in_terms(ctx, terms)
    if billed is None:
        return _indeterminate("R19", "Monto de la factura no disponible en la moneda pactada.")

    tol = terms.tolerance.abs if terms.tolerance is not None else 0.0
    calc = format_calculation_detail(terms, ctx.metered_lines, expected)
    quote = ctx.metered_lines[0].source_span
    evidence = CheckEvidence(clause=terms.contract_clause, quote=quote)

    if billed > expected + tol + _AMOUNT_TOLERANCE:
        detail = f"{calc} La factura cobra {terms.currency} {billed:g}."
        return CheckResult(  # type: ignore[arg-type]
            rule="R19",
            name=RULE_NAMES["R19"],
            result="FALLA",
            detail=detail,
            on_fail=ctx.rules.on_fail.R19,
            evidence=evidence,
        )

    if billed < expected - _AMOUNT_TOLERANCE:
        detail = f"{calc} La factura cobra {terms.currency} {billed:g} (por debajo del esperado)."
        return _ok("R19", detail)

    return _ok("R19", f"{calc} La factura cobra {terms.currency} {billed:g}.")


def check_r20(ctx: RuleContext) -> CheckResult:
    """T7.4 (D059) — First payment for an audited allowlist addition needs human OK."""
    addition = find_vendor_addition(ctx.rules, ctx.extraction.beneficiary)
    if addition is None:
        return _ok("R20", "Proveedor no agregado por onboarding auditado.")
    onboarding = ctx.rules.vendor_onboarding
    if onboarding is not None and not onboarding.first_invoice_requires_approval:
        return _ok("R20", "Onboarding sin aprobación obligatoria del primer pago.")
    if has_vendor_human_approval_after(ctx.ledger, addition.beneficiary, addition.added_at):
        return _ok(
            "R20",
            f"El proveedor {addition.beneficiary} ya tiene aprobación humana posterior al alta.",
        )
    return _fail(
        ctx,
        "R20",
        f"Primer pago de {addition.beneficiary}: falta aprobación humana tras el alta auditado.",
    )


CHECKS = (
    check_r01,
    check_r02,
    check_r03,
    check_r04,
    check_r05,
    check_r06,
    check_r07,
    check_r08,
    check_r09,
    check_r10,
    check_r11,
    check_r12,
    check_r13,
)
