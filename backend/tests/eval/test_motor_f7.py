"""T7.6 — f7 split runner: enabled_features gates evaluation; dev untouched."""

from __future__ import annotations

from app.motor.golden_runner import run_golden_split


def test_motor_f7_reports_zero_total_with_no_enabled_features() -> None:
    """``data/golden/f7.json`` starts with ``enabled_features: []`` (T7.6 §2)."""
    report = run_golden_split("f7")
    assert report.split == "f7"
    assert report.total == 0
    assert report.matched == 0
    assert report.unsafe_pay == 0
    assert report.failures == ()


def test_motor_dev_still_34_34_unsafe_pay_zero_after_f7() -> None:
    """Adding the f7 split must not change the frozen dev golden result (G2)."""
    report = run_golden_split("dev")
    assert report.total == 34
    assert report.matched == 34
    assert report.unsafe_pay == 0
