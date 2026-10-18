"""T1.2 — `data/rules.json` loads; malformed packages are rejected."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from app.models.rules_config import RulesConfig, load_rules_config
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = REPO_ROOT / "data" / "rules.json"
COMPANY_PATH = REPO_ROOT / "data" / "company.json"

EXPECTED_ON_FAIL = {
    "R01": "FRENAR",
    "R02": "ESCALAR",
    "R03": "ESCALAR",
    "R04": "ESCALAR",
    "R05": "FRENAR",
    "R06": "ESCALAR",
    "R07": "FRENAR",
    "R08": "ESCALAR",
    "R09": "ESCALAR",
    "R10": "ESCALAR",
    "R11": "ESCALAR",
    "R12": "FRENAR",
    "R13": "ESCALAR",
    "R14": "ESCALAR",
    "R15": "ESCALAR",
    "R16": "FRENAR",
    "R17": "FRENAR",
    "R19": "FRENAR",
}

EXPECTED_JEV = {
    "J1": 0.9,
    "J2": 0.9,
    "J3": 0.85,
    "J4": 0.85,
    "J6": 0.85,
    "J7": 0.5,
}


def _rules_dict() -> dict[str, Any]:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def test_load_live_rules_json() -> None:
    rules = load_rules_config(RULES_PATH)
    assert rules.limits.per_payment == 5000
    assert rules.limits.per_period.type == "calendar_month"
    assert rules.limits.per_period.amount == 20000
    assert rules.human_approval_threshold == 3000
    assert rules.manual_blocks == []
    assert rules.on_fail.model_dump() == EXPECTED_ON_FAIL
    assert rules.jev_thresholds.model_dump() == EXPECTED_JEV
    assert "J5" not in rules.jev_thresholds.model_dump()


def test_shared_fields_match_company_json() -> None:
    rules = load_rules_config(RULES_PATH)
    company = json.loads(COMPANY_PATH.read_text(encoding="utf-8"))
    assert rules.company.name == company["name"]
    assert rules.company.base_currency == company["base_currency"]
    assert rules.department_budgets == company["department_budgets"]
    assert rules.approvers == company["approvers"]
    assert rules.allowed_beneficiaries == company["allowed_beneficiaries"]
    assert "admin_notice_mailbox" not in json.loads(RULES_PATH.read_text(encoding="utf-8"))


def test_rejects_missing_per_payment() -> None:
    payload = _rules_dict()
    del payload["limits"]["per_payment"]
    with pytest.raises(ValidationError):
        RulesConfig.model_validate(payload)


def test_rejects_illegal_on_fail_pagar() -> None:
    payload = _rules_dict()
    payload["on_fail"]["R04"] = "PAGAR"
    with pytest.raises(ValidationError):
        RulesConfig.model_validate(payload)


def test_rejects_unexpected_top_level_field() -> None:
    payload = _rules_dict()
    payload["foo"] = 1
    with pytest.raises(ValidationError):
        RulesConfig.model_validate(payload)


def test_rejects_empty_allowed_beneficiaries() -> None:
    payload = _rules_dict()
    payload["allowed_beneficiaries"] = []
    with pytest.raises(ValidationError):
        RulesConfig.model_validate(payload)


@pytest.mark.parametrize("threshold", [0, -1])
def test_rejects_non_positive_human_approval_threshold(threshold: float) -> None:
    payload = _rules_dict()
    payload["human_approval_threshold"] = threshold
    with pytest.raises(ValidationError):
        RulesConfig.model_validate(payload)


def test_rejects_on_fail_missing_rule() -> None:
    payload = _rules_dict()
    del payload["on_fail"]["R13"]
    with pytest.raises(ValidationError):
        RulesConfig.model_validate(payload)


def test_rejects_jev_threshold_above_one() -> None:
    payload = _rules_dict()
    payload["jev_thresholds"]["J1"] = 1.5
    with pytest.raises(ValidationError):
        RulesConfig.model_validate(payload)


def test_rejects_period_type_other_than_calendar_month() -> None:
    payload = _rules_dict()
    payload["limits"]["per_period"]["type"] = "rolling_30d"
    with pytest.raises(ValidationError):
        RulesConfig.model_validate(payload)


def test_rejects_threshold_above_per_payment_limit() -> None:
    """T5.9 (D055): cross-field validator, no document previously relied on this gap."""
    payload = _rules_dict()
    payload["human_approval_threshold"] = payload["limits"]["per_payment"] + 1
    with pytest.raises(ValidationError):
        RulesConfig.model_validate(payload)


def test_accepts_threshold_equal_to_per_payment_limit() -> None:
    payload = _rules_dict()
    payload["human_approval_threshold"] = payload["limits"]["per_payment"]
    rules = RulesConfig.model_validate(payload)
    assert rules.human_approval_threshold == payload["limits"]["per_payment"]
