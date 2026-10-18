"""T2.3 — Run the 13 deterministic checks in fixed order.

T7.1 (D059): R14 is appended, never inserted in the middle or substituted,
when `ctx.rules.approval_policy` is set. Without a policy this returns
exactly the same 13-item list as before T7.1 (criterion 2 of
docs/T7_1_SPEC.md).
"""

from __future__ import annotations

from app.models.domain import CheckResult
from app.rules.checks import CHECKS, check_r14
from app.rules.context import RuleContext


def run_deterministic_checks(ctx: RuleContext) -> list[CheckResult]:
    results = [check(ctx) for check in CHECKS]
    if ctx.rules.approval_policy is not None:
        results.append(check_r14(ctx))
    return results
