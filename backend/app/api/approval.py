"""T7.1 (D059) §4 — «x de N» approval status and route eligibility.

Owned by API. Reads the R14 evidence frozen in a `DecisionRecord` (I2: never
rewrites it) plus the *live* `approval_policy`/`approver_groups` to report how
many eligible approvals are still missing, and to gate who may call
`approve`/`reject` once a record has a route in FALLA. Fail-closed (I3):
illegible R14 evidence never reports `satisfied=True`, and the route-specific
gate below never widens who may act beyond `data/company.json`'s groups.

Records without `approval_policy` (no R14 check, or R14 is OK/absent) keep
the pre-T7.1 behavior unchanged: `route_id=None`, `required=1`, any known
approver may act, and nothing here blocks a second approval from a
different author.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.api.schemas import ApprovalStatusBody
from app.models.domain import CheckResult, DecisionRecord, HumanAction
from app.models.rules_config import RulesConfig
from app.rules.approval_policy import parse_r14_quote

ApprovalError = str  # "approver_not_in_route" | "already_approved" | "approval_closed"


def find_r14_check(record: DecisionRecord) -> CheckResult | None:
    return next((c for c in record.checks if c.rule == "R14"), None)


def is_rejected(record: DecisionRecord) -> bool:
    return any(event.action == "rechazada_humano" for event in record.human_events)


def pending_checks(record: DecisionRecord) -> list[str]:
    """Checks a payment still needs OK on, excluding R04/R14 (§4: `payment_ready`)."""
    return [
        check.rule
        for check in record.checks
        if check.rule not in ("R04", "R14") and check.result != "OK"
    ]


def union_members(
    group_names: list[str], approver_groups: Mapping[str, frozenset[str]]
) -> frozenset[str]:
    members: set[str] = set()
    for name in group_names:
        members.update(approver_groups.get(name, frozenset()))
    return frozenset(members)


def _distinct_approver_emails(
    record: DecisionRecord, eligible: frozenset[str] | None
) -> set[str]:
    emails: set[str] = set()
    for event in record.human_events:
        if event.action != "aprobada_humano":
            continue
        if eligible is not None and event.author not in eligible:
            continue
        emails.add(event.author)
    return emails


def _live_route_min_approvals(rules: RulesConfig, route_id: str | None) -> int:
    policy = rules.approval_policy
    if policy is None or route_id is None:
        return 0
    for route in policy.routes:
        if route.id != route_id:
            continue
        if route.require.mode == "approvals" and route.require.min_approvals is not None:
            return route.require.min_approvals
        return 0
    return 0


def build_approval_status(
    record: DecisionRecord,
    *,
    rules: RulesConfig,
    approver_groups: Mapping[str, frozenset[str]],
) -> ApprovalStatusBody:
    rejected = is_rejected(record)
    pending = pending_checks(record)
    check = find_r14_check(record)

    if check is None or check.result != "FALLA":
        emails = _distinct_approver_emails(record, None)
        required = 1
        satisfied = len(emails) >= required
        return ApprovalStatusBody(
            route_id=None,
            required=required,
            collected=len(emails),
            approvers=sorted(emails),
            satisfied=satisfied,
            rejected=rejected,
            payment_ready=satisfied and not rejected and not pending,
            pending_checks=pending,
        )

    route_id = check.evidence.clause if check.evidence else None
    parsed = parse_r14_quote(check.evidence.quote if check.evidence else None)
    if parsed is None:
        # Fail-closed (I3, §4): illegible evidence never reports satisfied.
        return ApprovalStatusBody(
            route_id=route_id,
            required=0,
            collected=0,
            approvers=[],
            satisfied=False,
            rejected=rejected,
            payment_ready=False,
            pending_checks=pending,
        )
    frozen_min, frozen_groups = parsed
    eligible = union_members(frozen_groups, approver_groups)
    required = max(frozen_min, _live_route_min_approvals(rules, route_id))
    emails = _distinct_approver_emails(record, eligible)
    satisfied = len(emails) >= required
    return ApprovalStatusBody(
        route_id=route_id,
        required=required,
        collected=len(emails),
        approvers=sorted(emails),
        satisfied=satisfied,
        rejected=rejected,
        payment_ready=satisfied and not rejected and not pending,
        pending_checks=pending,
    )


def enforce_route_approval(
    record: DecisionRecord,
    author: str,
    action: HumanAction,
    *,
    rules: RulesConfig,
    approver_groups: Mapping[str, frozenset[str]],
) -> ApprovalError | None:
    """Route-specific gate for `approve`/`reject` (§4). None means "allowed".

    Only applies when the record has R14 in FALLA; otherwise behavior is
    unchanged from before T7.1 (caller still runs the global
    `_require_known_approver` allowlist check and the existing
    `decision == "ESCALAR"` gate).
    """
    check = find_r14_check(record)
    if check is None or check.result != "FALLA":
        return None

    route_id = check.evidence.clause if check.evidence else None
    parsed = parse_r14_quote(check.evidence.quote if check.evidence else None)
    if parsed is None:
        return "approval_closed"  # fail-closed: cannot determine the requirement

    frozen_min, frozen_groups = parsed
    eligible = union_members(frozen_groups, approver_groups)
    required = max(frozen_min, _live_route_min_approvals(rules, route_id))
    approved_emails = _distinct_approver_emails(record, eligible)
    rejected = is_rejected(record)

    if len(approved_emails) >= required or rejected:
        return "approval_closed"
    if author not in eligible:
        return "approver_not_in_route"
    if action == "aprobada_humano" and author in approved_emails:
        return "already_approved"
    if action == "rechazada_humano" and any(
        event.author == author and event.action == "rechazada_humano"
        for event in record.human_events
    ):
        return "already_approved"
    return None
