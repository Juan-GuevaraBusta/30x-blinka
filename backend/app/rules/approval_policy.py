"""T7.1 (D059) — Pure route resolution for R14. No LLM, no decide(), no I/O.

`approver_groups` membership (which emails belong to which group) lives in
`data/company.json`, never in `rules.json` (same reasoning as T5.9's
approvers allowlist: `PUT /rules` is mutable at runtime). This module only
resolves which *route* applies and formats its requirement; the API layer
(`app.api.approval`) is the one that resolves group names to emails.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.domain import Extraction
from app.models.rules_config import ApprovalPolicy, ApprovalRoute, RouteMatch
from app.rules.normalize import normalize_beneficiary


@dataclass(frozen=True)
class RouteResolution:
    """Either the first matching route, or a reason resolution could not proceed."""

    route: ApprovalRoute | None
    reason: str | None = None


def _missing_match_field(
    match: RouteMatch, extraction: Extraction, amount_base: float | None
) -> str | None:
    if (match.amount_base_gte is not None or match.amount_base_lt is not None) and (
        amount_base is None
    ):
        return "Monto en moneda base no disponible para evaluar la ruta de aprobación."
    if match.department is not None and extraction.department is None:
        return "Departamento ausente para evaluar la ruta de aprobación."
    if match.beneficiary is not None and extraction.beneficiary is None:
        return "Beneficiario ausente para evaluar la ruta de aprobación."
    if match.invoice_type is not None and extraction.invoice_type is None:
        return "Tipo de factura ausente para evaluar la ruta de aprobación."
    return None


def _route_matches(
    match: RouteMatch, extraction: Extraction, amount_base: float | None
) -> bool:
    if match.amount_base_gte is not None and not (
        amount_base is not None and amount_base >= match.amount_base_gte
    ):
        return False
    if match.amount_base_lt is not None and not (
        amount_base is not None and amount_base < match.amount_base_lt
    ):
        return False
    if match.department is not None and extraction.department != match.department:
        return False
    if match.beneficiary is not None and normalize_beneficiary(
        extraction.beneficiary
    ) != normalize_beneficiary(match.beneficiary):
        return False
    return not (
        match.invoice_type is not None and extraction.invoice_type != match.invoice_type
    )


def resolve_route(
    policy: ApprovalPolicy, extraction: Extraction, amount_base: float | None
) -> RouteResolution:
    """First route whose `match` is satisfied wins (docs/T7_1_SPEC.md §2-3).

    A route whose `match` needs a datum the extraction lacks makes the whole
    resolution indeterminate instead of silently skipping to the next route
    (fail-closed, I3): that earlier route might have matched had the datum
    been present, and jumping ahead could silently pick the wrong one.
    """
    for route in policy.routes:
        reason = _missing_match_field(route.match, extraction, amount_base)
        if reason is not None:
            return RouteResolution(route=None, reason=reason)
        if _route_matches(route.match, extraction, amount_base):
            return RouteResolution(route=route)
    return RouteResolution(
        route=None, reason="Ninguna ruta de la política coincide y no hay catch-all."
    )


def parse_r14_quote(quote: str | None) -> tuple[int, list[str]] | None:
    """Parse the canonical ``min_approvals=N;groups=a,b`` evidence quote (§3).

    Groups are returned in the order stored in the quote (sorted, by
    construction of `app.rules.checks.check_r14`). Returns ``None`` for any
    malformed or illegible input -- callers must fail closed on that.
    """
    if quote is None:
        return None
    fields: dict[str, str] = {}
    for part in quote.split(";"):
        if "=" not in part:
            return None
        key, _, value = part.partition("=")
        fields[key] = value
    if "min_approvals" not in fields or "groups" not in fields:
        return None
    try:
        min_approvals = int(fields["min_approvals"])
    except ValueError:
        return None
    groups = [name for name in fields["groups"].split(",") if name]
    if min_approvals < 1 or not groups:
        return None
    return min_approvals, groups


class ApprovalPolicyGroupError(ValueError):
    """Raised at boot when `approval_policy` references an invalid approver group."""


def validate_policy_groups(
    policy: ApprovalPolicy | None, groups: dict[str, frozenset[str]]
) -> None:
    """Loader-time cross-check against `data/company.json`'s `approver_groups` (§2).

    Every `from_groups` entry must exist, and `min_approvals` must be
    reachable by the distinct members of the union of those groups.
    """
    if policy is None:
        return
    for route in policy.routes:
        if route.require.mode != "approvals":
            continue
        unknown = [name for name in route.require.from_groups if name not in groups]
        if unknown:
            raise ApprovalPolicyGroupError(
                f'approval_policy route "{route.id}": unknown approver group(s) {unknown}'
            )
        union_members: set[str] = set()
        for name in route.require.from_groups:
            union_members.update(groups.get(name, frozenset()))
        min_approvals = route.require.min_approvals or 0
        if min_approvals > len(union_members):
            raise ApprovalPolicyGroupError(
                f'approval_policy route "{route.id}": min_approvals={min_approvals} '
                f"exceeds available distinct members ({len(union_members)})"
            )
