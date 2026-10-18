"""Shared demo fixtures for `seed_demo.py` (T10) and `generate_seed_sql.py` (T11).

Both scripts build the *same* demo `RulesConfig` and the *same* 3 vendor
agreement terms from this one module, and both validate them through the
real Pydantic models here -- neither script ever hand-serializes a dict that
skipped validation.

Demo vendors (fictitious, no real data per I6):
  * Globex LLC     -- monthly retainer.
  * Andesbyte SAS  -- hourly, with an overtime multiplier and a period cap.
  * Cuotasur SAS   -- quarterly installments with a total cap.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from app.api.tenancy import DEMO_BASE_CURRENCY, DEMO_COMPANY_NAME
from app.models.agreement import (
    AgreementInstallmentItem,
    HourlyAgreement,
    InstallmentsAgreement,
    OvertimeTerms,
    RetainerAgreement,
    VendorAgreement,
)
from app.models.rules_config import (
    ApprovalPolicy,
    ApprovalRoute,
    CompanyRef,
    RouteMatch,
    RouteRequire,
    RulesConfig,
    load_rules_config,
)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
RULES_PATH: Final[Path] = REPO_ROOT / "data" / "rules.json"
COMPANY_PATH: Final[Path] = REPO_ROOT / "data" / "company.json"

DEMO_VENDOR_NAMES: Final[tuple[str, str, str]] = (
    "Globex LLC",
    "Andesbyte SAS",
    "Cuotasur SAS",
)

# Approval-policy route id for the demo "2-of-N high amount" rule, and the
# company.json approver groups it requires approvals from.
_HIGH_AMOUNT_ROUTE_ID: Final[str] = "monto-alto"
_HIGH_AMOUNT_GROUPS: Final[tuple[str, str]] = ("finanzas", "cfo")
_HIGH_AMOUNT_THRESHOLD: Final[float] = 3000.0


class NoApproverEmailsError(Exception):
    """`data/company.json` has no usable approver email (empty approvers/approver_groups)."""

    def __init__(self) -> None:
        super().__init__("no_approver_emails_in_company_json")


def load_company(path: Path | None = None) -> dict:
    """Read `data/company.json` at runtime (never hardcode its contents)."""
    source = path if path is not None else COMPANY_PATH
    return json.loads(source.read_text(encoding="utf-8"))


def pick_approver_email(company: dict | None = None) -> str:
    """One real approver email from `data/company.json`'s `approvers` values
    union `approver_groups` members -- the same allowlist `app.api.asgi`
    computes for `confirmed_by`/`author`. Prefers the configured "default"
    approver when present, otherwise the lowest email (deterministic)."""
    data = company if company is not None else load_company()
    emails: set[str] = set()
    approvers = data.get("approvers")
    if isinstance(approvers, dict):
        emails.update(v for v in approvers.values() if isinstance(v, str))
    groups = data.get("approver_groups")
    if isinstance(groups, dict):
        for members in groups.values():
            if isinstance(members, list):
                emails.update(m for m in members if isinstance(m, str))
    if not emails:
        raise NoApproverEmailsError()
    default = approvers.get("default") if isinstance(approvers, dict) else None
    if isinstance(default, str) and default in emails:
        return default
    return sorted(emails)[0]


def build_demo_rules_config(base: RulesConfig | None = None) -> RulesConfig:
    """Demo `RulesConfig`: the real `data/rules.json` (frozen eval data, left
    on disk unmodified), with its `company` identity swapped to the live
    demo company (`DEMO_COMPANY_NAME`/`DEMO_BASE_CURRENCY` -- the
    `data/rules.json` template keeps its own frozen company name, used only
    by the eval motor), plus the 3 demo vendors on `allowed_beneficiaries`,
    plus the live demo `approval_policy`: high amount (2 of finanzas/cfo),
    Andesbyte variable (1 of finanzas), Marketing (1 of cfo) and an automatic
    catch-all -- the same 4 routes applied in production."""
    source = base if base is not None else load_rules_config(RULES_PATH)
    allowed = list(source.allowed_beneficiaries)
    for name in DEMO_VENDOR_NAMES:
        if name not in allowed:
            allowed.append(name)
    policy = ApprovalPolicy(
        routes=[
            ApprovalRoute(
                id=_HIGH_AMOUNT_ROUTE_ID,
                match=RouteMatch(amount_base_gte=_HIGH_AMOUNT_THRESHOLD),
                require=RouteRequire(
                    mode="approvals",
                    min_approvals=2,
                    from_groups=list(_HIGH_AMOUNT_GROUPS),
                ),
            ),
            ApprovalRoute(
                id="variable-andesbyte",
                match=RouteMatch(beneficiary="Andesbyte SAS"),
                require=RouteRequire(mode="approvals", min_approvals=1, from_groups=["finanzas"]),
            ),
            ApprovalRoute(
                id="marketing-cfo",
                match=RouteMatch(department="Marketing"),
                require=RouteRequire(mode="approvals", min_approvals=1, from_groups=["cfo"]),
            ),
            ApprovalRoute(
                id="resto-automatico", match=RouteMatch(), require=RouteRequire(mode="auto")
            ),
        ]
    )
    updated = source.model_copy(
        update={
            "company": CompanyRef(name=DEMO_COMPANY_NAME, base_currency=DEMO_BASE_CURRENCY),
            "allowed_beneficiaries": allowed,
            "approval_policy": policy,
        }
    )
    # Re-validate through the real model instead of trusting `model_copy`.
    return RulesConfig.model_validate(updated.model_dump(mode="json"))


def build_demo_agreements() -> dict[str, VendorAgreement]:
    """`vendor_key -> validated VendorAgreement` for the 3 demo vendors."""
    retainer = RetainerAgreement(
        vendor_name="Globex LLC",
        currency="USD",
        periodicity="monthly",
        amount={"min": 1200, "max": 1200},
        valid_from="2026-01-01",
    )
    hourly = HourlyAgreement(
        vendor_name="Andesbyte SAS",
        currency="USD",
        rate=45,
        included_hours=160,
        overtime=OvertimeTerms(multiplier=1.5, max_hours=40),
        period_cap=10000,
        valid_from="2026-01-01",
    )
    installments = InstallmentsAgreement(
        kind="installments",
        vendor_name="Cuotasur SAS",
        currency="USD",
        items=[
            AgreementInstallmentItem(
                key="q1", due_from="2026-01-01", due_to="2026-03-31", amount=2500
            ),
            AgreementInstallmentItem(
                key="q2", due_from="2026-04-01", due_to="2026-06-30", amount=2500
            ),
            AgreementInstallmentItem(
                key="q3", due_from="2026-07-01", due_to="2026-09-30", amount=2500
            ),
            AgreementInstallmentItem(
                key="q4", due_from="2026-10-01", due_to="2026-12-31", amount=2500
            ),
        ],
        total_cap=10000,
        valid_from="2026-01-01",
    )
    return {
        retainer.vendor_key: retainer,
        hourly.vendor_key: hourly,
        installments.vendor_key: installments,
    }
