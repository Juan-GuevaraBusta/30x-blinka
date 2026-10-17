"""T2.3 — Run the 13 deterministic checks in fixed order."""

from __future__ import annotations

from app.models.domain import CheckResult
from app.rules.checks import CHECKS
from app.rules.context import RuleContext


def run_deterministic_checks(ctx: RuleContext) -> list[CheckResult]:
    return [check(ctx) for check in CHECKS]
