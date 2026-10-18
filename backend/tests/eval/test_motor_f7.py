"""T7.6/T7.1–T7.3 — f7 split runner: enabled_features gates evaluation; dev untouched."""

from __future__ import annotations

import json
from pathlib import Path

from app.motor.golden_runner import run_golden_split

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_f7_golden_enabled_features_lists_t71_t72_and_t73() -> None:
    """T7.1–T7.3 (D059) enable their own feature once implemented."""
    golden = json.loads((REPO_ROOT / "data" / "golden" / "f7.json").read_text(encoding="utf-8"))
    assert golden["enabled_features"] == ["T7.1", "T7.2", "T7.3"]


def test_motor_f7_evaluates_all_sixteen_cases_unsafe_pay_zero() -> None:
    """With T7.1–T7.3 enabled, all 16 f7 golden entries must pass."""
    report = run_golden_split("f7")
    assert report.split == "f7"
    assert report.total == 16
    assert report.matched == 16
    assert report.unsafe_pay == 0
    assert report.failures == ()


def test_motor_dev_still_34_34_unsafe_pay_zero_after_f7() -> None:
    """Adding the f7 split must not change the frozen dev golden result (G2)."""
    report = run_golden_split("dev")
    assert report.total == 34
    assert report.matched == 34
    assert report.unsafe_pay == 0
