"""T2.5 — Pure decide() from check results only (I2)."""

from __future__ import annotations

import ast
from pathlib import Path

from app.models.domain import SEVERITY, CheckResult
from app.rules.decide import decide
from hypothesis import given
from hypothesis import strategies as st

DECIDE_SRC = Path(__file__).resolve().parents[2] / "app" / "rules" / "decide.py"
FORBIDDEN_IMPORT_ROOTS = frozenset(
    {
        "langchain",
        "langgraph",
        "openai",
        "anthropic",
        "app.graph",
        "app.extraction",
        "app.jev",
        "app.verifier",
    }
)

RULE_CODES = tuple(f"R{i:02d}" for i in range(1, 14))


def _check(
    rule: str,
    result: str,
    *,
    on_fail: str | None = None,
) -> CheckResult:
    payload: dict = {
        "rule": rule,
        "name": "Test",
        "result": result,
        "detail": "detalle.",
    }
    if on_fail is not None:
        payload["on_fail"] = on_fail
    return CheckResult.model_validate(payload)


def test_decide_pagar_when_all_ok() -> None:
    checks = [_check("R01", "OK"), _check("R02", "OK")]
    assert decide(checks) == "PAGAR"


def test_decide_escalar_on_empty_checks() -> None:
    assert decide([]) == "ESCALAR"


def test_decide_escalar_on_indeterminado() -> None:
    assert decide([_check("R06", "INDETERMINADO")]) == "ESCALAR"


def test_decide_frenar_on_falla_with_on_fail_frenar() -> None:
    assert decide([_check("R01", "FALLA", on_fail="FRENAR")]) == "FRENAR"


def test_decide_escalar_on_falla_with_on_fail_escalar() -> None:
    assert decide([_check("R02", "FALLA", on_fail="ESCALAR")]) == "ESCALAR"


def test_decide_frenar_wins_over_escalar() -> None:
    checks = [
        _check("R01", "FALLA", on_fail="FRENAR"),
        _check("R02", "FALLA", on_fail="ESCALAR"),
    ]
    assert decide(checks) == "FRENAR"


def test_decide_falla_without_on_fail_defaults_escalar() -> None:
    assert decide([_check("R09", "FALLA")]) == "ESCALAR"


def test_i2_decide_module_has_no_llm_imports() -> None:
    tree = ast.parse(DECIDE_SRC.read_text(encoding="utf-8"), filename=str(DECIDE_SRC))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root not in FORBIDDEN_IMPORT_ROOTS
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            assert root not in FORBIDDEN_IMPORT_ROOTS


@given(
    statuses=st.lists(
        st.sampled_from(["OK", "FALLA", "INDETERMINADO"]),
        min_size=0,
        max_size=13,
    ),
)
def test_property_no_pagar_when_any_non_ok(statuses: list[str]) -> None:
    checks = []
    for i, status in enumerate(statuses):
        on_fail = "ESCALAR" if status == "FALLA" else None
        checks.append(_check(RULE_CODES[i % len(RULE_CODES)], status, on_fail=on_fail))
    outcome = decide(checks)
    if not statuses or any(s != "OK" for s in statuses):
        assert outcome != "PAGAR"
    else:
        assert outcome == "PAGAR"


@given(
    statuses=st.lists(
        st.sampled_from(["OK", "FALLA", "INDETERMINADO"]),
        min_size=1,
        max_size=8,
    ),
    on_fails=st.lists(st.sampled_from(["FRENAR", "ESCALAR"]), min_size=1, max_size=8),
)
def test_property_decision_is_max_severity(statuses: list[str], on_fails: list[str]) -> None:
    checks = []
    candidates: list[str] = ["PAGAR"]
    for i, status in enumerate(statuses):
        on_fail = on_fails[i % len(on_fails)] if status == "FALLA" else None
        checks.append(_check(RULE_CODES[i % len(RULE_CODES)], status, on_fail=on_fail))
        if status == "INDETERMINADO":
            candidates.append("ESCALAR")
        elif status == "FALLA":
            candidates.append(on_fail or "ESCALAR")
    expected = max(candidates, key=lambda d: SEVERITY[d])
    assert decide(checks) == expected
