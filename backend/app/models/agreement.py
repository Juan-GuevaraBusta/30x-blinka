"""T9.1 (D061) — Structured vendor agreement registry (Spec & Data).

`VendorAgreement` is the human-confirmed, structured shape of one vendor
agreement (retainer, hourly with overtime, installments/milestones, or unit
pricing). The LLM only ever *proposes* a draft (`app.extraction.agreement_draft`,
I7); nothing here is ever built from an unconfirmed LLM response. Compilation
into effective `RulesConfig` entries is `app.rules.agreements.compile_rules`
(pure, Rules Engine).

`vendor_key` is always derived from `vendor_name` via
`app.rules.normalize.normalize_beneficiary` -- any caller-supplied value is
discarded before validation, so two different-cased/accented spellings of
the same vendor can never silently diverge into two keys.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from app.models.rules_config import AmountRange, TieredTier
from app.rules.normalize import normalize_beneficiary

AgreementStatus = Literal["active", "superseded", "inactive"]
AgreementKind = Literal["retainer", "hourly", "installments", "milestones", "unit_pricing"]
_RETAINER_PERIODICITIES = ("monthly", "biweekly", "quarterly")


class OvertimeTerms(BaseModel):
    model_config = ConfigDict(extra="forbid")

    multiplier: float = Field(ge=1)
    max_hours: float | None = Field(default=None, gt=0)


class AgreementInstallmentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    due_from: date
    due_to: date
    amount: float = Field(gt=0)

    @model_validator(mode="after")
    def _window_valid(self) -> AgreementInstallmentItem:
        if self.due_from > self.due_to:
            raise ValueError("items[].due_from must be <= due_to")
        return self


class UnitPricingUnitRate(BaseModel):
    """Same shape as `UnitRateFormula` minus `cap` (that is `period_cap`, above it)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["unit_rate"] = "unit_rate"
    unit: str = Field(min_length=1)
    rate: float = Field(gt=0)


class UnitPricingTiered(BaseModel):
    """Same shape as `TieredFormula` minus `cap`."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["tiered"] = "tiered"
    unit: str = Field(min_length=1)
    tiers: list[TieredTier] = Field(min_length=1)


class _AgreementCommon(BaseModel):
    """Fields shared by every `kind` (§2). Not itself part of the discriminated union."""

    model_config = ConfigDict(extra="forbid")

    vendor_name: str = Field(min_length=1)
    vendor_key: str = ""
    department: str | None = None
    currency: str = Field(min_length=1)
    valid_from: date
    valid_to: date | None = None
    sender_emails: list[str] = Field(default_factory=list)
    source_clauses: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _derive_vendor_key(cls, data: Any) -> Any:
        """`vendor_key` is always computed from `vendor_name` (§2); never client input."""
        if isinstance(data, dict):
            data = dict(data)
            data["vendor_key"] = normalize_beneficiary(data.get("vendor_name")) or ""
        return data

    @model_validator(mode="after")
    def _common_invariants(self) -> _AgreementCommon:
        if not self.vendor_key:
            raise ValueError("vendor_name must normalize to a non-empty vendor_key")
        if self.valid_to is not None and self.valid_from > self.valid_to:
            raise ValueError("valid_from must be <= valid_to")
        if any(not email.strip() for email in self.sender_emails):
            raise ValueError("sender_emails entries must be non-empty")
        return self


class RetainerAgreement(_AgreementCommon):
    kind: Literal["retainer"] = "retainer"
    periodicity: Literal["monthly", "biweekly", "quarterly"]
    amount: AmountRange
    total_cap: float | None = Field(default=None, gt=0)


class HourlyAgreement(_AgreementCommon):
    kind: Literal["hourly"] = "hourly"
    unit: Literal["hora"] = "hora"
    rate: float = Field(gt=0)
    included_hours: float | None = Field(default=None, gt=0)
    overtime: OvertimeTerms | None = None
    period_cap: float | None = Field(default=None, gt=0)


class InstallmentsAgreement(_AgreementCommon):
    kind: Literal["installments", "milestones"]
    items: list[AgreementInstallmentItem] = Field(min_length=1)
    total_cap: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _unique_item_keys(self) -> InstallmentsAgreement:
        keys = [item.key for item in self.items]
        if len(set(keys)) != len(keys):
            raise ValueError("items[].key entries must be unique")
        return self


class UnitPricingAgreement(_AgreementCommon):
    kind: Literal["unit_pricing"] = "unit_pricing"
    formula: Annotated[
        UnitPricingUnitRate | UnitPricingTiered, Field(discriminator="kind")
    ]
    period_cap: float | None = Field(default=None, gt=0)


VendorAgreement = Annotated[
    RetainerAgreement | HourlyAgreement | InstallmentsAgreement | UnitPricingAgreement,
    Field(discriminator="kind"),
]

# `VendorAgreement` is a bare discriminated-union alias, not a `BaseModel`, so standalone
# (de)serialization (persistence `terms_json`, test fixtures) goes through this adapter
# instead of each caller re-declaring the same `TypeAdapter`.
VendorAgreementAdapter: TypeAdapter[
    RetainerAgreement | HourlyAgreement | InstallmentsAgreement | UnitPricingAgreement
] = TypeAdapter(VendorAgreement)


def parse_vendor_agreement(data: Any) -> VendorAgreement:
    return VendorAgreementAdapter.validate_python(data)


def vendor_agreement_json(agreement: VendorAgreement) -> str:
    return VendorAgreementAdapter.dump_json(agreement).decode("utf-8")


class VendorAgreementVersion(BaseModel):
    """One solo-anexar version row (§2 `vendor_agreement_version`), as a value
    object shared by `MemoryStore`/`SqlStore` and the `/agreements` API
    responses. Never mutated once confirmed -- a later confirm or deactivate
    appends a new version with its own `status`, it never edits this one.
    """

    model_config = ConfigDict(extra="forbid")

    vendor_key: str
    version: int = Field(ge=1)
    terms: VendorAgreement
    source_sha256: str | None = None
    spans: dict[str, str] = Field(default_factory=dict)
    confirmed_by: str = Field(min_length=1)
    confirmed_at: AwareDatetime
    status: AgreementStatus
