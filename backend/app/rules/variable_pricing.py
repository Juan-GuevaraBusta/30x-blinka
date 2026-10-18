"""T7.3 (D059) — Pure variable-pricing resolution and recomputation for R19."""

from __future__ import annotations

import re
import unicodedata

from app.models.metered import MeteredLine
from app.models.rules_config import (
    CommissionFormula,
    PricingFormula,
    PricingTerms,
    RulesConfig,
    TieredFormula,
    UnitRateFormula,
)
from app.rules.context import RuleContext
from app.rules.normalize import normalize_beneficiary, normalize_currency

_AMOUNT_TOLERANCE = 0.005


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


# Common unit spellings (Spanish/English, singular/plural, abbreviations) that
# name the same unit. Anything not listed is compared as-is after casefolding,
# so an unknown unit still mismatches (R19 INDETERMINADO, fail-closed).
_UNIT_SYNONYMS: dict[str, str] = {
    **dict.fromkeys(("hora", "horas", "hour", "hours", "h", "hr", "hrs"), "hora"),
    **dict.fromkeys(("unidad", "unidades", "unit", "units"), "unidad"),
    **dict.fromkeys(("dia", "dias", "day", "days"), "dia"),
}


def normalize_unit(raw: str) -> str:
    collapsed = _strip_accents(raw).casefold()
    collapsed = re.sub(r"\s+", " ", collapsed.strip())
    return _UNIT_SYNONYMS.get(collapsed.rstrip("."), collapsed)


def find_pricing_terms(rules: RulesConfig, beneficiary: str | None) -> PricingTerms | None:
    """Return the configured terms for this beneficiary, or None if R19 must not run."""
    if not rules.variable_pricing:
        return None
    norm = normalize_beneficiary(beneficiary)
    if norm is None:
        return None
    matches = [
        terms
        for terms in rules.variable_pricing
        if normalize_beneficiary(terms.beneficiary) == norm
    ]
    if not matches:
        return None
    if len(matches) > 1:
        return matches[0]
    return matches[0]


def _apply_cap(total: float, formula: PricingFormula) -> float:
    cap = getattr(formula, "cap", None)
    if cap is not None and total > cap:
        return cap
    return total


def expected_amount(terms: PricingTerms, lines: tuple[MeteredLine, ...]) -> float | None:
    """Pure recomputation from declared formula and metered lines (no LLM)."""
    if not lines:
        return None
    line = lines[0]
    formula = terms.formula

    if isinstance(formula, UnitRateFormula):
        if line.quantity is None:
            return None
        if normalize_unit(line.unit) != normalize_unit(formula.unit):
            return None
        total = float(line.quantity) * float(formula.rate)
        return _apply_cap(total, formula)

    if isinstance(formula, TieredFormula):
        if line.quantity is None:
            return None
        if normalize_unit(line.unit) != normalize_unit(formula.unit):
            return None
        remaining = float(line.quantity)
        prev_limit = 0.0
        total = 0.0
        for tier in formula.tiers:
            if tier.up_to is not None:
                band = float(tier.up_to) - prev_limit
                take = min(remaining, band)
                total += take * float(tier.rate)
                remaining -= take
                prev_limit = float(tier.up_to)
                if remaining <= 0:
                    break
            else:
                total += remaining * float(tier.rate)
                remaining = 0.0
                break
        return _apply_cap(total, formula)

    if isinstance(formula, CommissionFormula):
        if line.base_amount is None:
            return None
        if normalize_unit(line.unit) != normalize_unit(formula.base_label):
            return None
        total = float(line.base_amount) * float(formula.pct) / 100.0
        return _apply_cap(total, formula)

    return None


def _quote_valid(line: MeteredLine, doc_text: str) -> bool:
    span = line.source_span.strip()
    if not span:
        return False
    if not doc_text.strip():
        return True
    return span in doc_text


def invoice_amount_in_terms(ctx: RuleContext, terms: PricingTerms) -> float | None:
    inv_cur = normalize_currency(ctx.extraction.currency)
    terms_cur = normalize_currency(terms.currency)
    if inv_cur is None or terms_cur is None or inv_cur != terms_cur:
        return None
    if ctx.extraction.amount is None:
        return None
    return float(ctx.extraction.amount)


def _tolerance_abs(terms: PricingTerms) -> float:
    if terms.tolerance is None:
        return 0.0
    return float(terms.tolerance.abs)


def format_calculation_detail(
    terms: PricingTerms, lines: tuple[MeteredLine, ...], expected: float
) -> str:
    line = lines[0]
    formula = terms.formula
    cur = terms.currency
    clause = terms.contract_clause

    if isinstance(formula, UnitRateFormula):
        qty = line.quantity
        return (
            f"{qty:g} {formula.unit} × {cur} {formula.rate:g} = {cur} {expected:g} "
            f"(cláusula {clause})."
        )
    if isinstance(formula, TieredFormula):
        qty = line.quantity
        return (
            f"{qty:g} {formula.unit} según tramos pactados = {cur} {expected:g} "
            f"(cláusula {clause})."
        )
    base = line.base_amount
    return (
        f"{formula.pct:g}% de {formula.base_label} ({cur} {base:g}) = {cur} {expected:g} "
        f"(cláusula {clause})."
    )


def validate_metered_for_terms(
    terms: PricingTerms, lines: tuple[MeteredLine, ...], doc_text: str
) -> str | None:
    """Return an INDETERMINADO reason, or None when inputs are usable."""
    if not lines:
        return "Sin líneas medidas para validar la fórmula variable."
    line = lines[0]
    if not _quote_valid(line, doc_text):
        return "La cita literal de la cantidad no aparece en el documento."
    formula = terms.formula
    if isinstance(formula, (UnitRateFormula, TieredFormula)) and normalize_unit(
        line.unit
    ) != normalize_unit(formula.unit):
        return "La unidad medida no coincide con la pactada en la fórmula."
    if isinstance(formula, CommissionFormula) and normalize_unit(
        line.unit
    ) != normalize_unit(formula.base_label):
        return "La base declarada no coincide con la etiqueta pactada."
    if expected_amount(terms, lines) is None:
        return "No se pudo leer cantidad o tarifa para recalcular el monto."
    return None
