"""Builders for API tests. No network and no .env."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from app.api import create_app
from app.api.schemas import InvoiceUpload, MetricsReading
from app.api.store import MemoryStore
from app.models.domain import Decision, DecisionRecord
from app.models.rules_config import RulesConfig
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[3]
RULES_PATH = REPO_ROOT / "data" / "rules.json"
COMPANY_PATH = REPO_ROOT / "data" / "company.json"

# T5.9 (D055): fixed test double for ADMIN_API_KEY. Mutating-endpoint tests send it
# via ADMIN_HEADERS instead of weakening the auth check.
TEST_ADMIN_KEY = "test-admin-key"
ADMIN_HEADERS = {"X-Admin-Key": TEST_ADMIN_KEY}

_EXAMPLE: dict[str, object] = {
    "id": "dec_0042",
    "invoice_id": "INV-0042",
    "received_at": "2026-03-04T10:15:00Z",
    "decision": "ESCALAR",
    "severity": 1,
    "summary": "Escalada: USD 4.200 llega al umbral de aprobación humana.",
    "extracted": {
        "beneficiary": "Globex LLC",
        "amount": 4200.0,
        "currency": "USD",
        "amount_base": 4200.0,
        "fx": {"rate": 1.0, "date": "2026-03-01"},
        "due_date": "2026-03-20",
        "invoice_number": "GX-2231",
        "recipient": "Acme Demo Inc.",
        "source_spans": {"amount": "Total a pagar: USD 4.200,00"},
    },
    "checks": [
        {
            "rule": "R04",
            "name": "Aprobación humana por monto",
            "result": "FALLA",
            "detail": "USD 4.200 llega al umbral de USD 3.000.",
            "on_fail": "ESCALAR",
        }
    ],
    "jev_signals": [],
    "verifier": {"consistent": True, "issues": []},
    "admin_notice": None,
    "next_step": "Pendiente de aprobación de cfo@demo.test.",
    "trace": {"langsmith_run_id": None, "url": None},
    "versions": {
        "rules_version": "v3",
        "model_extractor": "extractor-demo",
        "model_verifier": "verifier-demo",
        "jev": "jev-demo",
    },
    "human_events": [],
}

_SEVERITY: dict[str, int] = {"PAGAR": 0, "ESCALAR": 1, "FRENAR": 2}


class Processor(Protocol):
    def __call__(self, upload: InvoiceUpload) -> DecisionRecord: ...


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def load_rules() -> RulesConfig:
    return RulesConfig.model_validate_json(RULES_PATH.read_text(encoding="utf-8"))


def rules_payload() -> dict[str, object]:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def load_approver_emails() -> frozenset[str]:
    """Valid `author` values for approve/reject (T5.9, D055): data/company.json's approvers."""
    payload = json.loads(COMPANY_PATH.read_text(encoding="utf-8"))
    return frozenset(payload["approvers"].values())


def make_record(
    *,
    id: str = "dec_0042",
    invoice_id: str = "INV-0042",
    decision: Decision = "ESCALAR",
) -> DecisionRecord:
    payload = json.loads(json.dumps(_EXAMPLE))
    payload["id"] = id
    payload["invoice_id"] = invoice_id
    payload["decision"] = decision
    payload["severity"] = _SEVERITY[decision]
    return DecisionRecord.model_validate(payload)


def build_client(
    *,
    store: MemoryStore | None = None,
    processor: Processor | None = None,
    clock: MutableClock | None = None,
    rate_limit: int = 1000,
    metrics_reader: Callable[[], MetricsReading] | None = None,
    admin_api_key: str | None = TEST_ADMIN_KEY,
    approver_emails: frozenset[str] | None = None,
) -> tuple[TestClient, MemoryStore, MutableClock]:
    rules_store = store if store is not None else MemoryStore(load_rules())
    frozen = clock if clock is not None else MutableClock(datetime(2026, 3, 4, 12, 0, tzinfo=UTC))

    def default_processor(upload: InvoiceUpload) -> DecisionRecord:
        return make_record(invoice_id=upload.invoice_id)

    chosen = processor if processor is not None else default_processor
    allowed_approvers = approver_emails if approver_emails is not None else load_approver_emails()
    app = create_app(
        rules_store,
        chosen,
        clock=frozen,
        rate_limit=rate_limit,
        metrics_reader=metrics_reader,
        admin_api_key=admin_api_key,
        approver_emails=allowed_approvers,
    )
    return TestClient(app), rules_store, frozen
