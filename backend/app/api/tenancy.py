"""T9.8 (D067): company-based multi-tenancy primitives.

A user belongs to exactly one company (MVP). The company owns its rules,
agreements and decisions. A company without its own rules document is
*unconfigured*: its invoices are decided with a fail-closed fallback config
(R01 fails with ESCALAR) and any PAGAR is raised to ESCALAR -- never paid.
"""

from __future__ import annotations

import re
import unicodedata
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Literal

from app.models.domain import DecisionRecord
from app.models.rules_config import RulesConfig

DEMO_COMPANY_ID = "demo-acme"
DEMO_COMPANY_NAME = "Acme Demo Inc."
DEMO_BASE_CURRENCY = "USD"
CREATOR_GROUPS: tuple[str, ...] = ("finanzas", "cfo")

Role = Literal["admin", "member"]
ROLES: frozenset[str] = frozenset({"admin", "member"})

UNCONFIGURED_SUMMARY_PREFIX = (
    "Configura tu empresa para que el agente pueda decidir pagos: faltan beneficiarios "
    "permitidos, presupuestos y aprobadores. Mientras tanto, cada factura queda en "
    "revisión humana."
)
_FALLBACK_BENEFICIARY = "Empresa sin configurar"
_FALLBACK_APPROVER = "sin-configurar@blinka.invalid"

# The company the current invoice is being decided for. Set by
# `app.api.app._decide_and_store_invoice` around the processor call so the
# production processor (whose signature is `(upload, owner_id)`) reads the
# right company's rules and ledger. Defaults to the demo company, which is
# what every pre-T9.8 caller (tests, CLI) implicitly used.
CURRENT_COMPANY: ContextVar[str] = ContextVar("blinka_current_company", default=DEMO_COMPANY_ID)


@dataclass(frozen=True)
class Company:
    id: str
    name: str
    base_currency: str
    is_demo: bool
    created_by: str | None
    created_at: str


@dataclass(frozen=True)
class Member:
    company_id: str
    user_id: str
    email: str
    role: str
    approver_groups: tuple[str, ...]
    created_at: str

    @property
    def is_approver(self) -> bool:
        return bool(self.approver_groups)


class CompanyNameTakenError(Exception):
    pass


class AlreadyMemberError(Exception):
    pass


class CompanyNotFoundError(Exception):
    pass


def normalize_company_name(name: str) -> str:
    """Casefold, strip accents and collapse whitespace: «ACME  Demo» == «acme demo»."""
    decomposed = unicodedata.normalize("NFKD", name)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", stripped).strip().casefold()


def draft_rules_payload(template: RulesConfig, company: Company) -> dict[str, Any]:
    """`GET /rules` for an unconfigured company: identity fields empty, safe
    limits/threshold/on_fail/JEV from the template. Never another company's
    beneficiaries, budgets, approvers or policy."""
    base = template.model_dump(mode="json")
    base.update(
        {
            "company": {"name": company.name, "base_currency": company.base_currency},
            "allowed_beneficiaries": [],
            "department_budgets": {},
            "approvers": {},
            "manual_blocks": [],
            "approval_policy": None,
            "payment_series": [],
            "variable_pricing": [],
            "vendor_onboarding": None,
            "vendor_additions": [],
        }
    )
    return base


def fallback_rules(template: RulesConfig, company: Company) -> RulesConfig:
    """Fail-closed config to decide an unconfigured company's invoices: no real
    beneficiary is allowed and R01 fails with ESCALAR (never FRENAR: the vendor
    is not blocked, the company is just not configured yet)."""
    payload = draft_rules_payload(template, company)
    payload["company"]["name"] = company.name or _FALLBACK_BENEFICIARY
    payload["allowed_beneficiaries"] = [_FALLBACK_BENEFICIARY]
    payload["approvers"] = {"default": _FALLBACK_APPROVER}
    payload["on_fail"] = {**payload["on_fail"], "R01": "ESCALAR"}
    return RulesConfig.model_validate(payload)


def apply_unconfigured_guard(record: DecisionRecord) -> DecisionRecord:
    """Raise PAGAR to ESCALAR (severity only goes up, I4) and prefix the summary."""
    update: dict[str, Any] = {}
    if record.decision == "PAGAR":
        update["decision"] = "ESCALAR"
        update["severity"] = 1
    if not record.summary.startswith(UNCONFIGURED_SUMMARY_PREFIX):
        update["summary"] = f"{UNCONFIGURED_SUMMARY_PREFIX} {record.summary}"
    if not update:
        return record
    return DecisionRecord.model_validate({**record.model_dump(mode="json"), **update})


def approver_groups_for(
    members: list[Member],
    static_groups: dict[str, frozenset[str]] | None = None,
) -> dict[str, frozenset[str]]:
    groups: dict[str, set[str]] = {k: set(v) for k, v in (static_groups or {}).items()}
    for member in members:
        for group in member.approver_groups:
            groups.setdefault(group, set()).add(member.email)
    return {k: frozenset(v) for k, v in groups.items()}
