"""Pure eval scorer (T5.1.1, docs/T5_1_SPEC.md §4, §6, §8 criterion 3).

QA & Eval owns this module. Functions here are pure: no network, no reading
of ``data/golden/holdout.json`` or ``data/invoices/holdout/``, and no import
of ``app.llm``, ``app.graph``, ``app.extraction`` or ``app.jev``. The only
project import is ``app.gate.invariants.explanation_covers_failed_checks``
(reused, not reimplemented, for the ``summary`` half of ``explain_ok``) plus
the frozen ``CheckResult`` schema.

A ``record`` dict here mirrors ``DecisionRecord.model_dump(mode="json")``:
keys ``decision``, ``summary``, ``extracted``, ``checks`` (list of
``{"rule", "name", "result", "detail", ...}``), ``human_events``,
``verifier`` (``{"consistent": bool, "issues": [...]}``) and ``versions``.
``record`` is ``None`` when the run has no decision for that invoice (a
failed/absent run, never an invented ``PAGAR``).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.gate.invariants import explanation_covers_failed_checks
from app.models.domain import CheckResult, Decision

#: R01-R13 are the rules this task tracks for holdout coverage (docs/T5_1_SPEC.md §6).
HOLDOUT_RULE_CODES: tuple[str, ...] = tuple(f"R{i:02d}" for i in range(1, 14))
#: "duplicado probable" is the R05 sub-case tagged via the golden entry's
#: ``case`` field (e.g. ``dup_probable``); the rule code alone (R05) does not
#: distinguish it from an exact duplicate.
DUPLICADO_PROBABLE_LABEL = "duplicado probable"

DECISIONS: tuple[Decision, ...] = ("PAGAR", "ESCALAR", "FRENAR")
NO_RECORD = "sin registro"


@dataclass(frozen=True)
class EvalCase:
    """One golden row joined with the obtained decision (or ``None``)."""

    invoice_id: str
    expected_decision: Decision
    expected_rules: tuple[str, ...] = ()
    record: dict | None = None


@dataclass(frozen=True)
class CaseError:
    """One row entering the errors list (docs/T5_1_SPEC.md §6, errors section)."""

    invoice_id: str
    split: str
    expected_decision: str
    obtained_decision: str
    expected_rules: tuple[str, ...]
    failed_rules: tuple[str, ...]
    cause: str


@dataclass(frozen=True)
class SplitScore:
    """All metrics for one split (dev or holdout)."""

    split: str
    n: int
    unsafe_pay: int
    autonomy: float
    over_escalation: float | None
    under_severity: float | None
    reason_accuracy: float
    explain_ok: float
    matrix: dict[str, dict[str, int]]
    errors: tuple[CaseError, ...] = field(default_factory=tuple)


def _obtained_decision(case: EvalCase) -> str:
    if case.record is None:
        return NO_RECORD
    return str(case.record["decision"])


def _failed_rules(record: dict) -> set[str]:
    return {
        check["rule"] for check in record.get("checks", []) if check.get("result") != "OK"
    }


def count_unsafe_pay(cases: Sequence[EvalCase]) -> int:
    """PAGAR obtained with expected_decision != PAGAR. ESCALAR/FRENAR/absent never count."""
    return sum(
        1
        for case in cases
        if case.record is not None
        and case.record["decision"] == "PAGAR"
        and case.expected_decision != "PAGAR"
    )


def autonomy_pct(cases: Sequence[EvalCase]) -> float:
    """decision == expected_decision AND human_events is empty. Denominator: n."""
    if not cases:
        return 0.0
    hits = sum(
        1
        for case in cases
        if case.record is not None
        and case.record["decision"] == case.expected_decision
        and len(case.record.get("human_events", [])) == 0
    )
    return 100.0 * hits / len(cases)


def over_escalation_pct(cases: Sequence[EvalCase]) -> float | None:
    """Among expected PAGAR rows, % obtained ESCALAR/FRENAR/absent. n/a if none expected."""
    pagar_rows = [case for case in cases if case.expected_decision == "PAGAR"]
    if not pagar_rows:
        return None
    hits = sum(
        1
        for case in pagar_rows
        if case.record is None or case.record["decision"] in ("ESCALAR", "FRENAR")
    )
    return 100.0 * hits / len(pagar_rows)


def under_severity_pct(cases: Sequence[EvalCase]) -> float | None:
    """Among expected FRENAR rows, % obtained ESCALAR (only). n/a if none expected."""
    frenar_rows = [case for case in cases if case.expected_decision == "FRENAR"]
    if not frenar_rows:
        return None
    hits = sum(
        1
        for case in frenar_rows
        if case.record is not None and case.record["decision"] == "ESCALAR"
    )
    return 100.0 * hits / len(frenar_rows)


def reason_accuracy_pct(cases: Sequence[EvalCase]) -> float:
    """Set of non-OK checks[].rule == set(expected_rules). Order ignored. Denominator: n."""
    if not cases:
        return 0.0
    hits = sum(
        1
        for case in cases
        if case.record is not None and _failed_rules(case.record) == set(case.expected_rules)
    )
    return 100.0 * hits / len(cases)


def _explain_ok_for_record(record: dict) -> bool:
    summary = record.get("summary") or ""
    if not summary:
        return False
    if record.get("extracted") is None:
        return False
    checks = [CheckResult.model_validate(check) for check in record.get("checks", [])]
    for check in checks:
        if check.result == "OK":
            continue
        detail = check.detail or ""
        detail_covers = bool(detail) and check.rule in detail
        # Reuse explanation_covers_failed_checks (not reimplemented) for the
        # "rule id present in summary" half: with a single non-OK check it
        # reduces exactly to `check.rule in summary`.
        summary_covers = explanation_covers_failed_checks(summary, [check])
        if not (detail_covers or summary_covers):
            return False
    return True


def explain_ok_pct(cases: Sequence[EvalCase]) -> float:
    """summary non-empty, extracted present, and every failed check explained. Denominator: n."""
    if not cases:
        return 0.0
    hits = sum(
        1
        for case in cases
        if case.record is not None and _explain_ok_for_record(case.record)
    )
    return 100.0 * hits / len(cases)


def build_matrix(cases: Sequence[EvalCase]) -> dict[str, dict[str, int]]:
    """3x3 expected x obtained matrix, plus a "sin registro" column. Sums to len(cases)."""
    columns = (*DECISIONS, NO_RECORD)
    matrix: dict[str, dict[str, int]] = {
        expected: dict.fromkeys(columns, 0) for expected in DECISIONS
    }
    for case in cases:
        obtained = _obtained_decision(case)
        matrix[case.expected_decision][obtained] += 1
    return matrix


def rules_with_zero_cases(golden_entries: Sequence[dict]) -> list[str]:
    """R01-R13 (and "duplicado probable") absent from every expected_rules / case tag.

    ``golden_entries`` are the golden JSON ``entries`` (the ``case`` field, when
    present, is the only signal that distinguishes a probable duplicate from an
    exact one -- both use rule code R05).
    """
    seen_rules: set[str] = set()
    seen_probable = False
    for entry in golden_entries:
        seen_rules.update(entry.get("expected_rules", []))
        case_tag = str(entry.get("case", "")).lower()
        if "probable" in case_tag:
            seen_probable = True
    missing = [rule for rule in HOLDOUT_RULE_CODES if rule not in seen_rules]
    if not seen_probable:
        missing.append(DUPLICADO_PROBABLE_LABEL)
    return missing


def _case_cause(case: EvalCase, *, autonomy_hit: bool, reason_hit: bool) -> str:
    causes: list[str] = []
    record = case.record
    if not autonomy_hit:
        if record is None:
            causes.append("sin registro")
        elif len(record.get("human_events", [])) != 0:
            causes.append("evento humano registrado")
        elif record["decision"] != case.expected_decision:
            causes.append(f"decision {record['decision']} != {case.expected_decision}")
    if not reason_hit:
        failed = sorted(_failed_rules(record)) if record is not None else []
        causes.append(f"reglas {failed} != esperadas {sorted(case.expected_rules)}")
    if record is not None and not record.get("verifier", {}).get("consistent", True):
        for issue in record["verifier"].get("issues", []):
            causes.append(f"verifier {issue.get('code')}/{issue.get('kind')}")
    return "; ".join(causes) if causes else "no cumple autonomy/reason_accuracy"


def build_errors(cases: Sequence[EvalCase], split: str) -> list[CaseError]:
    """Rows missing autonomy or reason_accuracy. Only ids/codes, never evidence/summary text."""
    errors: list[CaseError] = []
    for case in cases:
        record = case.record
        autonomy_hit = (
            record is not None
            and record["decision"] == case.expected_decision
            and len(record.get("human_events", [])) == 0
        )
        reason_hit = record is not None and _failed_rules(record) == set(case.expected_rules)
        if autonomy_hit and reason_hit:
            continue
        failed = tuple(sorted(_failed_rules(record))) if record is not None else ()
        errors.append(
            CaseError(
                invoice_id=case.invoice_id,
                split=split,
                expected_decision=case.expected_decision,
                obtained_decision=_obtained_decision(case),
                expected_rules=tuple(case.expected_rules),
                failed_rules=failed,
                cause=_case_cause(case, autonomy_hit=autonomy_hit, reason_hit=reason_hit),
            )
        )
    return errors


def score_split(cases: Sequence[EvalCase], split: str) -> SplitScore:
    return SplitScore(
        split=split,
        n=len(cases),
        unsafe_pay=count_unsafe_pay(cases),
        autonomy=autonomy_pct(cases),
        over_escalation=over_escalation_pct(cases),
        under_severity=under_severity_pct(cases),
        reason_accuracy=reason_accuracy_pct(cases),
        explain_ok=explain_ok_pct(cases),
        matrix=build_matrix(cases),
        errors=tuple(build_errors(cases, split)),
    )


def _fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f}%"


def _matrix_table(matrix: dict[str, dict[str, int]]) -> str:
    columns = (*DECISIONS, NO_RECORD)
    header = "| esperado \\ obtenido | " + " | ".join(columns) + " |"
    sep = "|---|" + "|".join("---" for _ in columns) + "|"
    rows = [header, sep]
    for expected in DECISIONS:
        row = matrix.get(expected, dict.fromkeys(columns, 0))
        rows.append(
            "| " + expected + " | " + " | ".join(str(row[col]) for col in columns) + " |"
        )
    return "\n".join(rows)


def _errors_section(score: SplitScore) -> str:
    if not score.errors:
        return f"Split {score.split}: sin errores de autonomy. (reason_accuracy igual, ver arriba)."
    lines = []
    for err in score.errors:
        lines.append(
            f"- `{err.invoice_id}` ({err.split}): esperado {err.expected_decision}"
            f" / obtenido {err.obtained_decision}; reglas esperadas"
            f" {list(err.expected_rules)}; reglas con resultado != OK"
            f" {list(err.failed_rules)}. Causa: {err.cause}."
        )
    return "\n".join(lines)


def render_report_markdown(
    *,
    dev: SplitScore,
    holdout: SplitScore | None,
    generated_at: str,
    schema_version: int | str,
    rules_version: str,
    holdout_missing_rules: Sequence[str],
    versions_by_split: dict[str, Sequence[tuple[str, str, str, str]]] | None = None,
    motor_summary: str | None = None,
    command: str = "python eval/run_eval.py --output eval/reports/latest.md",
) -> str:
    """Render eval/reports/latest.md per docs/T5_1_SPEC.md §6. Pure string building."""
    versions_by_split = versions_by_split or {}

    lines: list[str] = []
    lines.append("# Evaluación dev y holdout")
    lines.append("")
    lines.append(f"Fecha: {generated_at}")
    lines.append(f"Comando: `{command}`")
    lines.append("Frase: El holdout no se usó para calibrar umbrales.")
    lines.append("")
    lines.append("PAGAR en esta tabla es una decisión registrada. No hay movimiento de dinero.")
    lines.append("")
    lines.append("## Métricas")
    lines.append("")
    lines.append(
        "| split | n | unsafe_pay | autonomy | over_escalation | under_severity |"
        " reason_accuracy | explain_ok |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for score in (dev, holdout):
        if score is None:
            lines.append("| holdout | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")
            continue
        lines.append(
            f"| {score.split} | {score.n} | {score.unsafe_pay} | {_fmt_pct(score.autonomy)} |"
            f" {_fmt_pct(score.over_escalation)} | {_fmt_pct(score.under_severity)} |"
            f" {_fmt_pct(score.reason_accuracy)} | {_fmt_pct(score.explain_ok)} |"
        )
    lines.append("")
    lines.append("## Referencia del motor")
    lines.append("")
    if motor_summary:
        lines.append(motor_summary)
    else:
        lines.append(
            "Salida de `eval/run_motor.py` en dev (y en holdout solo si T5.2 ya está"
            " cerrada); no medida en esta corrida. Es extracción verdadera (G2),"
            " no la autonomía del grafo."
        )
    lines.append("")
    lines.append("## Matriz esperado × obtenido")
    lines.append("")
    lines.append(f"### {dev.split}")
    lines.append("")
    lines.append(_matrix_table(dev.matrix))
    if holdout is not None:
        lines.append("")
        lines.append(f"### {holdout.split}")
        lines.append("")
        lines.append(_matrix_table(holdout.matrix))
    lines.append("")
    lines.append("## Cobertura del holdout")
    lines.append("")
    if holdout_missing_rules:
        lines.append(
            "Reglas con cero casos en `expected_rules` del holdout: "
            + ", ".join(holdout_missing_rules)
            + "."
        )
    else:
        lines.append("Todas las reglas rastreadas tienen al menos un caso en el holdout.")
    lines.append(
        "Esta tarea no reclama generalización para esas reglas: el holdout no las"
        " ejercita, así que un acierto en reason_accuracy o autonomy no dice nada"
        " sobre ellas."
    )
    lines.append("")
    lines.append("## Errores")
    lines.append("")
    lines.append(f"### {dev.split}")
    lines.append("")
    lines.append(_errors_section(dev))
    if holdout is not None:
        lines.append("")
        lines.append(f"### {holdout.split}")
        lines.append("")
        lines.append(_errors_section(holdout))
    lines.append("")
    lines.append("## Versiones")
    lines.append("")
    lines.append(f"schema_version: {schema_version}")
    lines.append(f"RULES_VERSION: {rules_version}")
    for split_name, tuples in versions_by_split.items():
        distinct = sorted(set(tuples))
        for rules_v, extractor, verifier, jev in distinct:
            lines.append(
                f"- {split_name}: rules_version={rules_v or 'no consta'}"
                f" model_extractor={extractor or 'no consta'}"
                f" model_verifier={verifier or 'no consta'} jev={jev or 'no consta'}"
            )
    lines.append("")
    lines.append("## Pendiente (no es el holdout)")
    lines.append("")
    lines.append("| Pieza | Estado |")
    lines.append("|---|---|")
    lines.append("| Adversariales | pendiente T5.3 |")
    lines.append("| Lectura ciega (`blind_read`) | pendiente T5.4 |")
    lines.append("| G5 | PENDIENTE |")
    lines.append("")
    return "\n".join(lines)
