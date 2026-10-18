"""T7.6/T7.1 — f7 split runner: enabled_features gates evaluation; dev untouched."""

from __future__ import annotations

import json
from pathlib import Path

from app.motor.golden_runner import run_golden_split

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_f7_golden_enabled_features_lists_t71_only() -> None:
    """T7.1 (D059) enables its own feature once implemented; T7.2/T7.3 do not exist yet."""
    golden = json.loads((REPO_ROOT / "data" / "golden" / "f7.json").read_text(encoding="utf-8"))
    assert golden["enabled_features"] == ["T7.1"]


def test_motor_f7_evaluates_only_the_three_t71_cases_unsafe_pay_zero() -> None:
    """Enabling T7.1 evaluates exactly its 3 cases (f7-012/013/014), gating out
    the 13 T7.2/T7.3 cases still disabled -- proving the enabled_features gate
    works, not just that the split reports a number."""
    report = run_golden_split("f7")
    assert report.split == "f7"
    assert report.total == 3
    assert report.matched == 3
    assert report.unsafe_pay == 0
    assert report.failures == ()


def test_motor_dev_still_34_34_unsafe_pay_zero_after_f7() -> None:
    """Adding the f7 split must not change the frozen dev golden result (G2)."""
    report = run_golden_split("dev")
    assert report.total == 34
    assert report.matched == 34
    assert report.unsafe_pay == 0
