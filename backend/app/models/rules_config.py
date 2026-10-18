"""Editable rules package (`data/rules.json`) per `docs/04` §2.

Schema validation only. Rule logic R01–R13 and `decide()` live in T2.x.
JEV thresholds are probabilities in (0, 1]. J5 has no threshold and is forbidden here.
`on_fail.R05` is a single key (exact-duplicate default FRENAR). Probable-duplicate
ESCALAR is catalog semantics in `docs/04` §3, not a second JSON key.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.domain import InvoiceType

FailAction = Literal["FRENAR", "ESCALAR"]
PeriodType = Literal["calendar_month"]
RouteApprovalMode = Literal["auto", "approvals"]


class CompanyRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    base_currency: str = Field(min_length=1)


class PeriodLimit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: PeriodType
    amount: float = Field(gt=0)


class Limits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    per_payment: float = Field(gt=0)
    per_period: PeriodLimit


class OnFail(BaseModel):
    """R01–R13 (required), plus R14 (optional, additive per T7.1/D059).

    Values are only FRENAR or ESCALAR. ``R14`` defaults to ``ESCALAR`` so
    every existing rules package without the key keeps parsing unchanged.
    """

    model_config = ConfigDict(extra="forbid")

    R01: FailAction
    R02: FailAction
    R03: FailAction
    R04: FailAction
    R05: FailAction
    R06: FailAction
    R07: FailAction
    R08: FailAction
    R09: FailAction
    R10: FailAction
    R11: FailAction
    R12: FailAction
    R13: FailAction
    R14: FailAction = "ESCALAR"


class RouteMatch(BaseModel):
    """All present fields combine with AND (T7.1 §2). Empty means catch-all."""

    model_config = ConfigDict(extra="forbid")

    amount_base_gte: float | None = None
    amount_base_lt: float | None = None
    beneficiary: str | None = None
    department: str | None = None
    invoice_type: InvoiceType | None = None

    def is_empty(self) -> bool:
        return all(
            value is None
            for value in (
                self.amount_base_gte,
                self.amount_base_lt,
                self.beneficiary,
                self.department,
                self.invoice_type,
            )
        )


class RouteRequire(BaseModel):
    """`auto` adds nothing; `approvals` needs >=1 approvals from non-empty groups."""

    model_config = ConfigDict(extra="forbid")

    mode: RouteApprovalMode
    min_approvals: int | None = Field(default=None, ge=1)
    from_groups: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def mode_consistency(self) -> RouteRequire:
        if self.mode == "auto":
            if self.min_approvals is not None or self.from_groups:
                raise ValueError('require.mode "auto" must not set min_approvals/from_groups')
            return self
        if self.min_approvals is None or self.min_approvals < 1:
            raise ValueError('require.mode "approvals" needs min_approvals >= 1')
        if not self.from_groups:
            raise ValueError('require.mode "approvals" needs a non-empty from_groups')
        if any(not group.strip() for group in self.from_groups):
            raise ValueError("from_groups entries must be non-empty")
        if len(set(self.from_groups)) != len(self.from_groups):
            raise ValueError("from_groups entries must be unique")
        return self


class ApprovalRoute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    match: RouteMatch = Field(default_factory=RouteMatch)
    require: RouteRequire


class ApprovalPolicy(BaseModel):
    """Routes evaluated in order; first match wins (T7.1 §2). Last route is catch-all."""

    model_config = ConfigDict(extra="forbid")

    routes: list[ApprovalRoute] = Field(min_length=1)

    @model_validator(mode="after")
    def catch_all_and_unique_ids(self) -> ApprovalPolicy:
        ids = [route.id for route in self.routes]
        if len(set(ids)) != len(ids):
            raise ValueError("approval_policy.routes ids must be unique")
        if not self.routes[-1].match.is_empty():
            raise ValueError(
                "approval_policy.routes must end with a catch-all route (empty match)"
            )
        return self


class JevThresholds(BaseModel):
    """J1, J2, J3, J4, J6, J7 only. J5 is not a payment threshold."""

    model_config = ConfigDict(extra="forbid")

    J1: float = Field(gt=0, le=1)
    J2: float = Field(gt=0, le=1)
    J3: float = Field(gt=0, le=1)
    J4: float = Field(gt=0, le=1)
    J6: float = Field(gt=0, le=1)
    J7: float = Field(gt=0, le=1)


class RulesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: CompanyRef
    limits: Limits
    human_approval_threshold: float = Field(gt=0)
    allowed_beneficiaries: list[str] = Field(min_length=1)
    department_budgets: dict[str, float]
    approvers: dict[str, str]
    manual_blocks: list[str]
    on_fail: OnFail
    jev_thresholds: JevThresholds
    approval_policy: ApprovalPolicy | None = None

    @field_validator("allowed_beneficiaries")
    @classmethod
    def beneficiaries_not_blank(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("allowed_beneficiaries entries must be non-empty")
        return value

    @field_validator("department_budgets")
    @classmethod
    def budgets_positive(cls, value: dict[str, float]) -> dict[str, float]:
        if any(amount <= 0 for amount in value.values()):
            raise ValueError("department_budgets amounts must be > 0")
        if any(not name.strip() for name in value):
            raise ValueError("department_budgets keys must be non-empty")
        return value

    @field_validator("approvers")
    @classmethod
    def default_approver_required(cls, value: dict[str, str]) -> dict[str, str]:
        if "default" not in value:
            raise ValueError('approvers must include a "default" key')
        if any(not name.strip() or not email.strip() for name, email in value.items()):
            raise ValueError("approver names and emails must be non-empty")
        return value

    @model_validator(mode="after")
    def threshold_within_per_payment_limit(self) -> RulesConfig:
        """T5.9 (D055): escalation threshold above the per-payment cap is never reachable."""
        if self.human_approval_threshold > self.limits.per_payment:
            raise ValueError("human_approval_threshold must be <= limits.per_payment")
        return self


def load_rules_config(path: Path) -> RulesConfig:
    """Load UTF-8 JSON and reject a malformed rules package."""
    return RulesConfig.model_validate_json(path.read_text(encoding="utf-8"))
