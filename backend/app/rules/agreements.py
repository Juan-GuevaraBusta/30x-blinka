"""T9.1 (D061) — Deterministic compilation of confirmed vendor agreements into
effective rules. Pure: no LLM, no network, no clock, no I/O.

`compile_rules(base, agreements)` is the single source of truth the motor and
the graph use (`app.api.production_processor.process_upload`): series, variable
pricing, allowed-beneficiary and vendor-onboarding sections compiled from
agreements are *added* to `base`, never replacing or removing anything already
written by hand in `rules.json`. Duplicate/fraud protections (R01 allowlist,
R05, R13, R19, R20) are therefore structurally unaffected by this module: it
never touches `on_fail`, `manual_blocks`, `limits`, or any existing
`payment_series`/`variable_pricing` entry, and it only ever appends to
`allowed_beneficiaries`/`vendor_additions`.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, time

from app.models.agreement import (
    HourlyAgreement,
    InstallmentsAgreement,
    RetainerAgreement,
    UnitPricingAgreement,
    VendorAgreement,
)
from app.models.rules_config import (
    PaymentSeries,
    PricingTerms,
    RulesConfig,
    SeriesItem,
    TieredFormula,
    TieredTier,
    UnitRateFormula,
    VendorAddition,
    VendorOnboarding,
)
from app.rules.context import ContractTerms
from app.rules.normalize import normalize_beneficiary


class AgreementConflictError(Exception):
    """§4: `base` already has a hand-written series/pricing entry for this vendor."""

    def __init__(self, vendor_key: str) -> None:
        self.vendor_key = vendor_key
        super().__init__(vendor_key)


@dataclass(frozen=True)
class ActiveAgreement:
    """One confirmed, active agreement version, paired with its own `version`.

    `compile_rules`'s ids must be stable (`agr-<vendor_key>-v<version>`, §4),
    and `version` is persistence metadata (`vendor_agreement_version.version`),
    not something `compile_rules` itself could derive -- it stays a pure
    function of its arguments by taking the version as plain input data here,
    the same way it takes `confirmed_by` for the audited `vendor_additions`
    entry it may add (never a clock or a network call).
    """

    agreement: VendorAgreement
    version: int
    confirmed_by: str
    # Literal quotes from the source document, validated at draft time and
    # persisted with the confirmed version (`vendor_agreement_version.spans`).
    spans: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CompiledRules:
    """`compile_rules`'s output: effective rules plus provenance.

    `rules` is what the motor and the graph must use instead of the raw,
    hand-edited `RulesConfig` (§4). `provenance` maps a compiled entry back to
    the agreement it came from (`GET /rules/effective`, §3), keyed
    `"payment_series:<vendor_key>"` / `"variable_pricing:<vendor_key>"` /
    `"allowed_beneficiaries:<vendor_key>"` -> `"agr-<vendor_key>-v<version>"`.
    """

    rules: RulesConfig
    provenance: dict[str, str]


def agreement_ref_id(vendor_key: str, version: int) -> str:
    return f"agr-{vendor_key}-v{version}"


def _clause_text(agreement: VendorAgreement, ref_id: str) -> str:
    """`evidence.clause` cites the agreement id and, if given, the source clause (§4)."""
    clauses = (
        ", ".join(sorted(agreement.source_clauses.values())) if agreement.source_clauses else None
    )
    return f"{ref_id} ({clauses})" if clauses else ref_id


def _hourly_formula(agreement: HourlyAgreement) -> UnitRateFormula | TieredFormula:
    if agreement.overtime is None:
        return UnitRateFormula(
            kind="unit_rate", unit="hora", rate=agreement.rate, cap=agreement.period_cap
        )
    included = agreement.included_hours or 0.0
    tiers: list[TieredTier] = []
    if included > 0:
        tiers.append(TieredTier(up_to=included, rate=agreement.rate))
    tiers.append(TieredTier(up_to=None, rate=agreement.rate * agreement.overtime.multiplier))
    return TieredFormula(kind="tiered", unit="hora", tiers=tiers, cap=_hourly_cap(agreement))


def _hourly_cap(agreement: HourlyAgreement) -> float | None:
    """§4: `min(period_cap, included_hours * rate + max_hours * rate * multiplier)`."""
    overtime = agreement.overtime
    if overtime is None or overtime.max_hours is None:
        return agreement.period_cap
    included = agreement.included_hours or 0.0
    overtime_cost = overtime.max_hours * agreement.rate * overtime.multiplier
    formula_cap = included * agreement.rate + overtime_cost
    if agreement.period_cap is None:
        return formula_cap
    return min(agreement.period_cap, formula_cap)


def _unit_pricing_formula(agreement: UnitPricingAgreement) -> UnitRateFormula | TieredFormula:
    formula = agreement.formula
    if formula.kind == "unit_rate":
        return UnitRateFormula(
            kind="unit_rate", unit=formula.unit, rate=formula.rate, cap=agreement.period_cap
        )
    return TieredFormula(
        kind="tiered",
        unit=formula.unit,
        tiers=[TieredTier(up_to=tier.up_to, rate=tier.rate) for tier in formula.tiers],
        cap=agreement.period_cap,
    )


def _added_at_for(agreement: VendorAgreement) -> datetime:
    """Deterministic, derived only from the agreement's own data (pure: no clock)."""
    return datetime.combine(agreement.valid_from, time.min, tzinfo=UTC)


def vendor_key_conflicts_with_base(rules: RulesConfig, vendor_key: str) -> bool:
    """§4: true when `rules` already has a hand-written series/pricing entry
    for `vendor_key`. Shared by `compile_rules` (defense in depth) and the
    store's confirm-time check (`agreement_conflicts_with_rules`, 409).
    """
    series_keys = {normalize_beneficiary(s.beneficiary) for s in rules.payment_series}
    pricing_keys = {normalize_beneficiary(p.beneficiary) for p in rules.variable_pricing}
    return vendor_key in series_keys or vendor_key in pricing_keys


def contract_terms_for_agreement(agreement: VendorAgreement) -> ContractTerms | None:
    """§4 R06: a single fixed amount (retainer min==max, or equal installments)."""
    if isinstance(agreement, RetainerAgreement):
        if agreement.amount.min != agreement.amount.max:
            return None
        amount = agreement.amount.min
    elif isinstance(agreement, InstallmentsAgreement):
        amounts = {item.amount for item in agreement.items}
        if len(amounts) != 1:
            return None
        amount = next(iter(amounts))
    else:
        return None
    return ContractTerms(
        beneficiary=agreement.vendor_name,
        fee_amount=amount,
        fee_currency=agreement.currency,
        cited_clauses=sorted(agreement.source_clauses.values()),
    )


_PERIODICITY_ES = {
    "monthly": "mensual",
    "biweekly": "quincenal",
    "quarterly": "trimestral",
    "annual": "anual",
}
# Draft span keys that quote the amount (retainer) or the installments.
_AMOUNT_SPAN_KEYS = ("amount_min", "amount_max", "items")
_CLAUSE_ID = re.compile(r"^[\d.,;\s]+$")


def _fmt_amount(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def _terms_rendering(agreement: VendorAgreement) -> str:
    """The confirmed amount as a plain contract sentence (no metadata, no ids)."""
    currency = agreement.currency
    if isinstance(agreement, RetainerAgreement):
        low, high = agreement.amount.min, agreement.amount.max
        period = _PERIODICITY_ES.get(agreement.periodicity, agreement.periodicity)
        if low == high:
            return f"La tarifa pactada es {_fmt_amount(low)} {currency} por periodo {period}."
        return (
            f"La tarifa pactada es de entre {_fmt_amount(low)} y {_fmt_amount(high)} "
            f"{currency} por periodo {period}."
        )
    if isinstance(agreement, InstallmentsAgreement):
        amounts = {item.amount for item in agreement.items}
        if len(amounts) == 1:
            amount = next(iter(amounts))
            return f"El monto pactado por cuota es {_fmt_amount(amount)} {currency}."
        listed = "; ".join(
            f"cuota {item.key}: {_fmt_amount(item.amount)} {currency}"
            for item in agreement.items
        )
        return f"Los montos pactados son {listed}."
    return f"Acuerdo {agreement.kind} pactado en {currency}."


def agreement_clause_text(active: ActiveAgreement) -> str:
    """Deterministic clause text J6 reads for a human-confirmed agreement.

    The UI does not send clause text, so citing `source_clauses` ids ("4.1")
    or nothing made the live JEV answer J6 false and every matching invoice
    escalate. Built only from the source document's literal quotes (draft
    spans validated verbatim, or clause text the confirming human typed in
    `source_clauses`) followed by the confirmed amount as a plain contract
    sentence. Bare clause ids and provenance are left out on purpose: the
    live JEV scored metadata-laden text below the J6 threshold. This only
    feeds J6; R06 keeps comparing the confirmed amount deterministically. Pure.
    """
    agreement = active.agreement
    parts: list[str] = []
    for key in _AMOUNT_SPAN_KEYS:
        quote = (active.spans.get(key) or "").strip()
        if quote and quote not in parts:
            parts.append(quote)
    for value in sorted(agreement.source_clauses.values()):
        text = value.strip()
        if text and not _CLAUSE_ID.match(text) and text not in parts:
            parts.append(text)
    rendering = _terms_rendering(agreement)
    if rendering not in parts:
        parts.append(rendering)
    return " ".join(parts)


def agreement_contract_map(
    agreements: Sequence[ActiveAgreement],
) -> dict[str, ContractTerms]:
    """vendor_key -> confirmed fixed-amount contract terms, for the graph's contract
    lookup (§4): "si el proveedor tiene acuerdo activo, se usan sus términos
    confirmados sin llamar al LLM". Agreements without a single fixed amount are
    absent here -- the caller falls back to `lookup_contract`, same as today.
    """
    result: dict[str, ContractTerms] = {}
    for active in agreements:
        terms = contract_terms_for_agreement(active.agreement)
        if terms is not None:
            result[active.agreement.vendor_key] = terms.model_copy(
                update={"clause_text": agreement_clause_text(active)}
            )
    return result


def compile_rules(base: RulesConfig, agreements: Sequence[ActiveAgreement]) -> CompiledRules:
    """Pure, deterministic. `compile_rules(base, [])` leaves `base` untouched (§4)."""
    if not agreements:
        return CompiledRules(rules=base, provenance={})

    new_series = list(base.payment_series)
    new_pricing = list(base.variable_pricing)
    allowed = list(base.allowed_beneficiaries)
    allowed_norm = {normalize_beneficiary(name) for name in allowed}
    additions = list(base.vendor_additions)
    onboarding = base.vendor_onboarding
    provenance: dict[str, str] = {}

    for active in agreements:
        agreement = active.agreement
        vendor_key = agreement.vendor_key
        if vendor_key_conflicts_with_base(base, vendor_key):
            raise AgreementConflictError(vendor_key)

        ref_id = agreement_ref_id(vendor_key, active.version)
        clause = _clause_text(agreement, ref_id)

        if isinstance(agreement, RetainerAgreement):
            new_series.append(
                PaymentSeries(
                    id=ref_id,
                    beneficiary=agreement.vendor_name,
                    department=agreement.department,
                    periodicity=agreement.periodicity,
                    currency=agreement.currency,
                    expected_amount=agreement.amount,
                    start=agreement.valid_from,
                    end=agreement.valid_to,
                    total_cap=agreement.total_cap,
                )
            )
            provenance[f"payment_series:{vendor_key}"] = ref_id
        elif isinstance(agreement, InstallmentsAgreement):
            items = [
                SeriesItem(
                    key=item.key, due_from=item.due_from, due_to=item.due_to, amount=item.amount
                )
                for item in agreement.items
            ]
            new_series.append(
                PaymentSeries(
                    id=ref_id,
                    beneficiary=agreement.vendor_name,
                    department=agreement.department,
                    periodicity=agreement.kind,
                    currency=agreement.currency,
                    total_cap=agreement.total_cap,
                    items=items,
                )
            )
            provenance[f"payment_series:{vendor_key}"] = ref_id
        elif isinstance(agreement, HourlyAgreement):
            new_pricing.append(
                PricingTerms(
                    beneficiary=agreement.vendor_name,
                    currency=agreement.currency,
                    contract_clause=clause,
                    formula=_hourly_formula(agreement),
                )
            )
            provenance[f"variable_pricing:{vendor_key}"] = ref_id
        else:  # UnitPricingAgreement
            new_pricing.append(
                PricingTerms(
                    beneficiary=agreement.vendor_name,
                    currency=agreement.currency,
                    contract_clause=clause,
                    formula=_unit_pricing_formula(agreement),
                )
            )
            provenance[f"variable_pricing:{vendor_key}"] = ref_id

        if vendor_key not in allowed_norm:
            allowed.append(agreement.vendor_name)
            allowed_norm.add(vendor_key)
            additions.append(
                VendorAddition(
                    beneficiary=agreement.vendor_name,
                    added_at=_added_at_for(agreement),
                    added_by=active.confirmed_by,
                    reason="Alta automática por acuerdo confirmado (T9.1).",
                    source_decision_id=f"agreement:{vendor_key}:v{active.version}",
                )
            )
            onboarding = VendorOnboarding(enabled=True, first_invoice_requires_approval=True)
            provenance[f"allowed_beneficiaries:{vendor_key}"] = ref_id

    rules = base.model_copy(
        update={
            "payment_series": new_series,
            "variable_pricing": new_pricing,
            "allowed_beneficiaries": allowed,
            "vendor_additions": additions,
            "vendor_onboarding": onboarding,
        }
    )
    return CompiledRules(rules=rules, provenance=provenance)
