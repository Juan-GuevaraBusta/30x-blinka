"""T5.1.1 — pure scorer tests (docs/T5_1_SPEC.md §6, §8 criterion 3).

Synthetic dicts only. Never opens data/golden/holdout.json or
data/invoices/holdout/, never imports app.llm / app.graph / app.extraction /
app.jev, never opens a socket.
"""

from __future__ import annotations

from app.gate.eval_score import (
    DUPLICADO_PROBABLE_LABEL,
    EvalCase,
    autonomy_pct,
    build_errors,
    build_matrix,
    count_unsafe_pay,
    explain_ok_pct,
    over_escalation_pct,
    reason_accuracy_pct,
    render_report_markdown,
    rules_with_zero_cases,
    score_split,
    under_severity_pct,
)


def _record(
    decision: str,
    *,
    failed_rules: dict[str, str] | None = None,
    summary: str = "Resumen sintético.",
    extracted: dict | None = None,
    human_events: list | None = None,
    consistent: bool = True,
    issues: list | None = None,
) -> dict:
    failed_rules = failed_rules or {}
    checks = [
        {
            "rule": rule,
            "name": "Chequeo sintético",
            "result": result,
            "detail": f"{rule} detalle sintético.",
        }
        for rule, result in failed_rules.items()
    ]
    return {
        "decision": decision,
        "summary": summary,
        "extracted": extracted if extracted is not None else {"beneficiary": "Acme Demo Inc."},
        "checks": checks,
        "human_events": human_events or [],
        "verifier": {"consistent": consistent, "issues": issues or []},
        "versions": {
            "rules_version": "v1",
            "model_extractor": "fake-extractor",
            "model_verifier": "fake-verifier",
            "jev": "fake-jev",
        },
    }


def _case(
    invoice_id: str,
    expected_decision: str,
    expected_rules: list[str] | None = None,
    record: dict | None = None,
) -> EvalCase:
    return EvalCase(
        invoice_id=invoice_id,
        expected_decision=expected_decision,
        expected_rules=tuple(expected_rules or []),
        record=record,
    )


# -- unsafe_pay ----------------------------------------------------------------


def test_unsafe_pay_counts_pagar_against_escalar_expected() -> None:
    cases = [_case("inv-1", "ESCALAR", record=_record("PAGAR"))]
    assert count_unsafe_pay(cases) == 1


def test_unsafe_pay_does_not_count_pagar_expected() -> None:
    cases = [_case("inv-1", "PAGAR", record=_record("PAGAR"))]
    assert count_unsafe_pay(cases) == 0


def test_unsafe_pay_does_not_count_escalar_against_frenar_expected() -> None:
    cases = [_case("inv-1", "FRENAR", record=_record("ESCALAR"))]
    assert count_unsafe_pay(cases) == 0


def test_unsafe_pay_does_not_count_missing_record() -> None:
    cases = [_case("inv-1", "ESCALAR", record=None)]
    assert count_unsafe_pay(cases) == 0


# -- autonomy -------------------------------------------------------------------


def test_autonomy_requires_matching_decision_and_empty_human_events() -> None:
    cases = [
        _case("inv-1", "PAGAR", record=_record("PAGAR")),
        _case(
            "inv-2",
            "PAGAR",
            record=_record("PAGAR", human_events=[{"author": "a", "action": "aprobada_humano"}]),
        ),
    ]
    assert autonomy_pct(cases) == 50.0


def test_autonomy_human_event_excludes_even_when_decision_matches() -> None:
    cases = [
        _case(
            "inv-1",
            "FRENAR",
            record=_record("FRENAR", human_events=[{"author": "a", "action": "rechazada_humano"}]),
        ),
    ]
    assert autonomy_pct(cases) == 0.0


def test_autonomy_missing_record_does_not_count() -> None:
    cases = [_case("inv-1", "PAGAR", record=None)]
    assert autonomy_pct(cases) == 0.0


# -- over_escalation -------------------------------------------------------------


def test_over_escalation_denominator_is_expected_pagar_rows() -> None:
    cases = [
        _case("inv-1", "PAGAR", record=_record("ESCALAR")),
        _case("inv-2", "PAGAR", record=_record("PAGAR")),
        _case("inv-3", "FRENAR", record=_record("FRENAR")),
    ]
    # denominator = 2 (the two expected PAGAR rows), not 3.
    assert over_escalation_pct(cases) == 50.0


def test_over_escalation_counts_missing_record_as_over_escalation() -> None:
    cases = [_case("inv-1", "PAGAR", record=None)]
    assert over_escalation_pct(cases) == 100.0


def test_over_escalation_na_when_no_pagar_expected() -> None:
    cases = [_case("inv-1", "ESCALAR", record=_record("ESCALAR"))]
    assert over_escalation_pct(cases) is None


# -- under_severity ---------------------------------------------------------------


def test_under_severity_denominator_is_expected_frenar_rows_and_counts_only_escalar() -> None:
    cases = [
        _case("inv-1", "FRENAR", record=_record("ESCALAR")),
        _case("inv-2", "FRENAR", record=_record("FRENAR")),
        _case("inv-3", "PAGAR", record=_record("PAGAR")),
    ]
    # denominator = 2 (expected FRENAR rows), not 3.
    assert under_severity_pct(cases) == 50.0


def test_under_severity_missing_record_does_not_count_as_escalar() -> None:
    cases = [_case("inv-1", "FRENAR", record=None)]
    assert under_severity_pct(cases) == 0.0


def test_under_severity_na_when_no_frenar_expected() -> None:
    cases = [_case("inv-1", "PAGAR", record=_record("PAGAR"))]
    assert under_severity_pct(cases) is None


# -- reason_accuracy ---------------------------------------------------------------


def test_reason_accuracy_compares_sets_regardless_of_order() -> None:
    cases = [
        _case(
            "inv-1",
            "ESCALAR",
            expected_rules=["R04", "R06"],
            record=_record("ESCALAR", failed_rules={"R06": "FALLA", "R04": "INDETERMINADO"}),
        )
    ]
    assert reason_accuracy_pct(cases) == 100.0


def test_reason_accuracy_fails_on_mismatched_set() -> None:
    cases = [
        _case(
            "inv-1",
            "ESCALAR",
            expected_rules=["R04"],
            record=_record("ESCALAR", failed_rules={"R06": "FALLA"}),
        )
    ]
    assert reason_accuracy_pct(cases) == 0.0


def test_reason_accuracy_missing_record_does_not_count() -> None:
    cases = [_case("inv-1", "ESCALAR", expected_rules=["R04"], record=None)]
    assert reason_accuracy_pct(cases) == 0.0


# -- explain_ok ---------------------------------------------------------------------


def test_explain_ok_true_when_detail_contains_failed_rule_id() -> None:
    cases = [
        _case(
            "inv-1",
            "ESCALAR",
            expected_rules=["R04"],
            record=_record("ESCALAR", failed_rules={"R04": "FALLA"}),
        )
    ]
    assert explain_ok_pct(cases) == 100.0


def test_explain_ok_true_via_summary_when_detail_is_generic(monkeypatch) -> None:
    record = _record("ESCALAR", failed_rules={"R04": "FALLA"}, summary="Revisar R04 con el equipo.")
    record["checks"][0]["detail"] = "sin información adicional"
    cases = [_case("inv-1", "ESCALAR", expected_rules=["R04"], record=record)]
    assert explain_ok_pct(cases) == 100.0


def test_explain_ok_false_when_rule_id_absent_from_detail_and_summary() -> None:
    record = _record("ESCALAR", failed_rules={"R04": "FALLA"})
    record["checks"][0]["detail"] = "sin información adicional"
    record["summary"] = "Resumen sin referencias a reglas."
    cases = [_case("inv-1", "ESCALAR", expected_rules=["R04"], record=record)]
    assert explain_ok_pct(cases) == 0.0


def test_explain_ok_false_when_summary_empty() -> None:
    record = _record("PAGAR", summary="")
    cases = [_case("inv-1", "PAGAR", record=record)]
    assert explain_ok_pct(cases) == 0.0


def test_explain_ok_false_when_extracted_missing() -> None:
    record = _record("PAGAR")
    record["extracted"] = None
    cases = [_case("inv-1", "PAGAR", record=record)]
    assert explain_ok_pct(cases) == 0.0


def test_explain_ok_missing_record_does_not_count() -> None:
    cases = [_case("inv-1", "PAGAR", record=None)]
    assert explain_ok_pct(cases) == 0.0


# -- matrix ---------------------------------------------------------------------------


def test_matrix_sums_to_batch_size() -> None:
    cases = [
        _case("inv-1", "PAGAR", record=_record("PAGAR")),
        _case("inv-2", "ESCALAR", record=_record("FRENAR")),
        _case("inv-3", "FRENAR", record=None),
    ]
    matrix = build_matrix(cases)
    total = sum(count for row in matrix.values() for count in row.values())
    assert total == len(cases)
    assert matrix["PAGAR"]["PAGAR"] == 1
    assert matrix["ESCALAR"]["FRENAR"] == 1
    assert matrix["FRENAR"]["sin registro"] == 1


# -- holdout coverage --------------------------------------------------------------------


def test_rules_with_zero_cases_lists_rules_absent_from_expected_rules() -> None:
    golden_entries = [
        {"case": "r01", "expected_rules": ["R01"]},
        {"case": "r04_only", "expected_rules": ["R04"]},
        {"case": "dup_exact", "expected_rules": ["R05"]},
    ]
    missing = rules_with_zero_cases(golden_entries)
    assert "R01" not in missing
    assert "R04" not in missing
    assert "R02" in missing
    assert "R13" in missing
    assert DUPLICADO_PROBABLE_LABEL in missing


def test_rules_with_zero_cases_credits_duplicado_probable_from_case_tag() -> None:
    golden_entries = [
        {"case": "dup_probable", "expected_rules": ["R05"]},
    ]
    missing = rules_with_zero_cases(golden_entries)
    assert DUPLICADO_PROBABLE_LABEL not in missing


# -- markdown ------------------------------------------------------------------------------


def test_markdown_includes_calibration_phrase_and_t5_3_pending_row() -> None:
    dev_cases = [_case("dev-001", "PAGAR", record=_record("PAGAR"))]
    dev_score = score_split(dev_cases, "dev")
    md = render_report_markdown(
        dev=dev_score,
        holdout=None,
        generated_at="2026-10-18",
        schema_version=1,
        rules_version="v1",
        holdout_missing_rules=["R02", "R03"],
    )
    assert "El holdout no se usó para calibrar umbrales." in md
    assert "pendiente T5.3" in md
    assert "PAGAR" in md and "decisión registrada" in md


def test_markdown_never_contains_evidence_or_summary_text() -> None:
    dev_cases = [
        _case(
            "dev-001",
            "FRENAR",
            expected_rules=["R01"],
            record=_record(
                "ESCALAR",
                failed_rules={"R01": "FALLA"},
                summary="texto secreto de la factura con una clave sk-ABC123",
            ),
        )
    ]
    dev_score = score_split(dev_cases, "dev")
    md = render_report_markdown(
        dev=dev_score,
        holdout=None,
        generated_at="2026-10-18",
        schema_version=1,
        rules_version="v1",
        holdout_missing_rules=[],
    )
    assert "texto secreto" not in md
    assert "sk-ABC123" not in md


def test_build_errors_includes_autonomy_and_reason_accuracy_misses() -> None:
    cases = [
        _case("dev-001", "PAGAR", record=_record("PAGAR")),  # hit, excluded
        _case("dev-002", "PAGAR", record=_record("ESCALAR")),  # autonomy miss
        _case(
            "dev-003",
            "ESCALAR",
            expected_rules=["R04"],
            record=_record("ESCALAR", failed_rules={"R06": "FALLA"}),
        ),  # reason_accuracy miss, autonomy hit (decision matches, no human events)
    ]
    errors = build_errors(cases, "dev")
    ids = {e.invoice_id for e in errors}
    assert ids == {"dev-002", "dev-003"}


def test_score_split_total_matches_denominator() -> None:
    cases = [
        _case("dev-001", "PAGAR", record=_record("PAGAR")),
        _case("dev-002", "FRENAR", record=None),
    ]
    score = score_split(cases, "dev")
    assert score.n == 2
    assert score.split == "dev"
