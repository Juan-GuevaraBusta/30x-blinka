"""T9.2 (D061) §8.4 — `data/inbox/dev/` end to end, deterministic extraction only.

No LLM, no network: every `es_factura` email is parsed with the real
`app.extraction.ingest.ingest_bytes` (the exact channel/content the inbox
would hand to the invoice pipeline), fields are pulled out with a small
deterministic regex extractor (mirrors `data/invoices/generate.py`'s own
"Beneficiario:/Numero:/Total:/Vence:/Departamento:" convention), and the real,
pure rules motor (`run_deterministic_checks` + `decide()`, same functions
`eval/run_motor.py` uses) decides. Gate: no non-factura email ever reaches a
decision, and no email in this dataset ever decides PAGAR (`unsafe_pay=0`).
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.extraction.ingest import ingest_bytes
from app.inbox.classifier import classify_email
from app.inbox.config import default_inbox_classifier_config
from app.inbox.parser import looks_like_pdf, parse_eml_bytes, select_document
from app.models.domain import Extraction, JevSignal
from app.rules.context import RuleContext
from app.rules.decide import decide
from app.rules.fx import load_fx_table
from app.rules.run_checks import run_deterministic_checks
from tests.api.support import load_rules

REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET_DIR = REPO_ROOT / "data" / "inbox" / "dev"

_FIELD_PATTERNS = {
    "beneficiary": re.compile(r"Beneficiario:\s*(.+)"),
    "invoice_number": re.compile(r"Numero:\s*(.+)"),
    "due_date": re.compile(r"Vence:\s*(\d{4}-\d{2}-\d{2})"),
    "department": re.compile(r"Departamento:\s*(.+)"),
    "recipient": re.compile(r"Destinatario:\s*(.+)"),
}
_AMOUNT_LINE = re.compile(r"Total:\s*([\d.,]+)\s*([A-Z]{3})")
_PERFECT_JEV_IDS = ("J1", "J2", "J3", "J4", "J7")


class _FakeLlm:
    def __init__(self, response: dict) -> None:
        self._response = response

    def complete_json(self, system: str, user: str) -> dict:
        return self._response


def _load_expected() -> list[dict]:
    return json.loads((DATASET_DIR / "expected.json").read_text(encoding="utf-8"))


def _perfect_jev() -> list[JevSignal]:
    return [JevSignal(id=jid, answer=True, probability=0.99) for jid in _PERFECT_JEV_IDS]  # type: ignore[arg-type]


def _extract_deterministic(text: str) -> Extraction:
    fields: dict[str, object] = {}
    for name, pattern in _FIELD_PATTERNS.items():
        match = pattern.search(text)
        if match:
            fields[name] = match.group(1).strip()
    amount_match = _AMOUNT_LINE.search(text)
    amount = None
    currency = None
    if amount_match:
        amount = float(amount_match.group(1).replace(",", ""))
        currency = amount_match.group(2)
    due_date = None
    if "due_date" in fields:
        from datetime import date

        due_date = date.fromisoformat(str(fields["due_date"]))
    return Extraction(
        beneficiary=fields.get("beneficiary"),  # type: ignore[arg-type]
        amount=amount,
        currency=currency,
        due_date=due_date,
        invoice_number=fields.get("invoice_number"),  # type: ignore[arg-type]
        recipient=fields.get("recipient"),  # type: ignore[arg-type]
        department=fields.get("department"),  # type: ignore[arg-type]
    )


def _decide_for_entry(entry: dict) -> tuple[str, list[str]]:
    """Real deterministic extraction + real rules motor for one `es_factura` entry."""
    raw = (DATASET_DIR / entry["file"]).read_bytes()
    parsed = parse_eml_bytes(raw)
    selected = select_document(parsed)
    ingested = ingest_bytes(selected.content, channel=selected.channel)
    extraction = _extract_deterministic(ingested.text)

    rules = load_rules()
    fx_table = load_fx_table()
    ctx = RuleContext(
        rules=rules,
        fx_table=fx_table,
        extraction=extraction,
        contract_terms=None,
        contract_confirmed=False,
        jev_signals=_perfect_jev(),
        doc_text=ingested.text,
        ledger=(),
        received_at=datetime(2026, 5, 15, tzinfo=UTC),
        manual_block=False,
        metered_lines=(),
    )
    checks = run_deterministic_checks(ctx)
    decision = decide(checks)
    failed = [c.rule for c in checks if c.result != "OK"]
    return decision, failed


def _classify_entry(entry: dict):
    raw = (DATASET_DIR / entry["file"]).read_bytes()
    parsed = parse_eml_bytes(raw)
    pdfs = tuple(a for a in parsed.attachments if looks_like_pdf(a))
    selected = select_document(parsed)
    return classify_email(
        parsed,
        config=default_inbox_classifier_config(),
        sender_emails=frozenset(entry.get("sender_emails", [])),
        allowed_beneficiaries=tuple(entry.get("allowed_beneficiaries", [])),
        pdf_attachments=pdfs,
        document_ambiguous=selected.ambiguous,
        llm=_FakeLlm(entry["llm_response"]) if entry.get("llm_response") else None,
    )


@pytest.mark.parametrize("entry", _load_expected(), ids=lambda e: e["file"])
def test_es_factura_entries_never_decide_pagar(entry: dict) -> None:
    result = _classify_entry(entry)
    assert result.classification == entry["classification"]
    if result.classification != "es_factura":
        pytest.skip("not routed to the invoice pipeline (no decision possible)")

    decision, failed_rules = _decide_for_entry(entry)
    assert decision != "PAGAR"
    if entry.get("expected_decision"):
        assert decision == entry["expected_decision"]
    for rule in entry.get("expected_rules", []):
        assert rule in failed_rules


def test_dataset_wide_unsafe_pay_is_zero() -> None:
    """Gate (I9-style, scoped to this dataset): no email here ever yields PAGAR,
    whether or not it was classified as a factura.
    """
    unsafe_pay = 0
    for entry in _load_expected():
        result = _classify_entry(entry)
        if result.classification != "es_factura":
            continue  # never reaches the invoice pipeline -> cannot be PAGAR
        decision, _failed = _decide_for_entry(entry)
        if decision == "PAGAR":
            unsafe_pay += 1
    assert unsafe_pay == 0
