"""JEV state assembly and threshold helpers (T3.5). No payment decisions."""

from __future__ import annotations

from collections.abc import Sequence

from app.config import ConfigError
from app.jev.decision_client import INVOICE_QUESTIONS, DecisionClient, JevQuestion
from app.llm import DecisionClientError
from app.models.domain import Extraction, JevSignal
from app.models.rules_config import JevThresholds

_THRESHOLD_IDS: tuple[str, ...] = ("J1", "J2", "J3", "J4", "J6", "J7")


class JevRunError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _field_line(label: str, value: str | None) -> str:
    if value is None:
        return f"{label}: null"
    return f"{label}: {value}"


def build_jev_state(
    *,
    extraction: Extraction,
    company_name: str,
    doc_text: str,
    cited_clause: str | None = None,
) -> str:
    amount_str = None if extraction.amount is None else format(extraction.amount, "g")
    due_str = None if extraction.due_date is None else extraction.due_date.isoformat()
    clause_value = (
        None if cited_clause is None or not cited_clause.strip() else cited_clause
    )

    lines = [
        "EXTRACTED_DATA:",
        _field_line("beneficiary", extraction.beneficiary),
        _field_line("amount", amount_str),
        _field_line("currency", extraction.currency),
        _field_line("due_date", due_str),
        _field_line("recipient", extraction.recipient),
        _field_line("company", company_name),
        _field_line("cited_clause", clause_value),
        "",
        "DOCUMENT:",
        doc_text,
    ]
    return "\n".join(lines)


def ask_invoice_signals(
    client: DecisionClient,
    state: str,
    *,
    questions: Sequence[JevQuestion] | None = None,
) -> list[JevSignal]:
    if not state.strip():
        raise JevRunError("empty_state")
    qs = questions if questions is not None else INVOICE_QUESTIONS
    try:
        return list(client.ask(state, qs))
    except (DecisionClientError, ConfigError):
        raise JevRunError("client_error") from None


def ids_below_threshold(
    signals: Sequence[JevSignal],
    thresholds: JevThresholds,
) -> list[str]:
    by_id: dict[str, JevSignal] = {}
    for signal in signals:
        by_id[signal.id] = signal

    below: list[str] = []
    for jev_id in _THRESHOLD_IDS:
        signal = by_id.get(jev_id)
        if signal is None:
            continue
        threshold = getattr(thresholds, jev_id)
        if signal.probability < threshold:
            below.append(jev_id)
    return below
