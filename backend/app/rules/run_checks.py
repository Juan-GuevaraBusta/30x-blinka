"""T2.3 — Run the 13 deterministic checks in fixed order.

T7.1 (D059): R14 is appended, never inserted in the middle or substituted,
when `ctx.rules.approval_policy` is set. Without a policy this returns
exactly the same 13-item list as before T7.1 (criterion 2 of
docs/T7_1_SPEC.md).

T7.2 (D059): R15-R18 are appended, in that fixed order, only when this
invoice's beneficiary (and department, if the series fixes one) resolves
to exactly one `payment_series` entry. Without `payment_series`, or for an
invoice whose beneficiary has no matching series, R15-R18 are never
emitted -- the check list stays exactly what it was before T7.2 (criterion
4 of docs/T7_2_SPEC.md). An ambiguous match (more than one series matches)
emits only R15 as INDETERMINADO -- R16-R18 need a single resolved series to
mean anything, and decide() already escalates on R15 alone (fail-closed, I3).
"""

from __future__ import annotations

from app.models.domain import CheckResult
from app.rules.checks import (
    CHECKS,
    check_r14,
    check_r15,
    check_r15_ambiguous_series,
    check_r16,
    check_r17,
    check_r18,
)
from app.rules.context import RuleContext
from app.rules.payment_series import find_matching_series


def run_deterministic_checks(ctx: RuleContext) -> list[CheckResult]:
    results = [check(ctx) for check in CHECKS]
    if ctx.rules.approval_policy is not None:
        results.append(check_r14(ctx))
    if ctx.rules.payment_series:
        resolution = find_matching_series(ctx.rules.payment_series, ctx.extraction)
        if resolution.ambiguous:
            results.append(check_r15_ambiguous_series())
        elif resolution.series is not None:
            series = resolution.series
            results.append(check_r15(ctx, series))
            results.append(check_r16(ctx, series))
            results.append(check_r17(ctx, series))
            results.append(check_r18(ctx, series))
    return results
