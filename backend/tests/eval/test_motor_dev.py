"""T2.8 — Motor matches golden dev labels (G2: 100 % autonomy, unsafe_pay=0)."""

from __future__ import annotations

from app.motor.golden_runner import run_golden_split


def test_motor_dev_autonomy_100_percent() -> None:
    report = run_golden_split("dev")
    assert report.total == 34
    assert report.unsafe_pay == 0
    assert report.matched == report.total, report.failures


def test_motor_dev_r06_fx_pay_cases_pagar() -> None:
    report = run_golden_split("dev")
    by_id = {r.invoice_id: r for r in report.failures}
    assert "dev-009" not in by_id
    assert "dev-010" not in by_id
