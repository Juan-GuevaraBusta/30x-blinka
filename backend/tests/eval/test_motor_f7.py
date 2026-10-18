"""T7.6/T7.1/T7.2 — f7 split runner: enabled_features gates evaluation; dev untouched."""

from __future__ import annotations

import json
from pathlib import Path

from app.motor.golden_runner import run_golden_split

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_f7_golden_enabled_features_lists_t71_and_t72() -> None:
    """T7.1 and T7.2 (D059) enable their own feature once implemented.

    T7.3 is not implemented yet.
    """
    golden = json.loads((REPO_ROOT / "data" / "golden" / "f7.json").read_text(encoding="utf-8"))
    assert golden["enabled_features"] == ["T7.1", "T7.2"]


def test_motor_f7_evaluates_only_the_t71_and_t72_cases_unsafe_pay_zero() -> None:
    """Enabling T7.1+T7.2 evaluates exactly their 11 cases (3 + 8), gating out
    the 5 T7.3 cases still disabled -- proving the enabled_features gate
    works, not just that the split reports a number."""
    report = run_golden_split("f7")
    assert report.split == "f7"
    assert report.total == 11
    assert report.matched == 11
    assert report.unsafe_pay == 0
    assert report.failures == ()


def test_motor_dev_still_34_34_unsafe_pay_zero_after_f7() -> None:
    """Adding the f7 split must not change the frozen dev golden result (G2)."""
    report = run_golden_split("dev")
    assert report.total == 34
    assert report.matched == 34
    assert report.unsafe_pay == 0
