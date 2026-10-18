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

FailAction = Literal["FRENAR", "ESCALAR"]
PeriodType = Literal["calendar_month"]


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
    """Exactly R01–R13. Values are only FRENAR or ESCALAR."""

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
