#!/usr/bin/env python3
"""CLI: run deterministic motor against golden dev (T2.8, G2)."""

from __future__ import annotations

import argparse
import sys

from app.motor.golden_runner import run_golden_split


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Golden motor runner (extraction ground truth).")
    parser.add_argument(
        "--split",
        default="dev",
        choices=("dev", "holdout", "f7"),
        help=(
            "Golden split (holdout reserved for F5; f7 is the synthetic series/"
            "variable-pay/approval-policy split from T7.6; default dev)."
        ),
    )
    args = parser.parse_args(argv)
    report = run_golden_split(args.split)
    print(
        f"split={report.split} total={report.total} matched={report.matched} "
        f"autonomy={report.autonomy_pct:.1f}% unsafe_pay={report.unsafe_pay}"
    )
    for failure in report.failures:
        print(
            f"  FAIL {failure.invoice_id}: {failure.detail} "
            f"(got {failure.actual_decision}/{failure.failed_rules}, "
            f"expected {failure.expected_decision}/{failure.expected_rules})"
        )
    return 0 if report.matched == report.total and report.unsafe_pay == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
