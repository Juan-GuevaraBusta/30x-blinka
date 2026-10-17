"""HTTP API. `decide()` is not called here: the injected processor already built the record."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from pydantic import ValidationError

from app.api.rate_limit import FixedWindowLimiter, RateLimitMiddleware
from app.api.schemas import (
    MAX_INVOICE_BYTES,
    HumanDecisionBody,
    InvoiceMeta,
    InvoiceRejected,
    InvoiceUpload,
    MetricsBody,
    MetricsReading,
)
from app.api.store import DuplicateDecisionError, MemoryStore
from app.models.domain import DecisionRecord, HumanAction, HumanEvent
from app.models.rules_config import RulesConfig

Processor = Callable[[InvoiceUpload], DecisionRecord]
Clock = Callable[[], datetime]
MetricsReader = Callable[[], MetricsReading | None]


def create_app(
    store: MemoryStore,
    processor: Processor,
    *,
    clock: Clock,
    rate_limit: int,
    metrics_reader: MetricsReader | None = None,
) -> FastAPI:
    """Build the app. Tests pass `store`, `processor`, `clock`, and `rate_limit`."""
    limiter = FixedWindowLimiter(rate_limit, clock)
    app = FastAPI(title="blinka-invoice-agent", openapi_url=None)
    app.add_middleware(RateLimitMiddleware, limiter=limiter)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/rules")
    def get_rules() -> RulesConfig:
        return store.rules

    @app.put("/rules")
    def put_rules(body: RulesConfig) -> RulesConfig:
        # FastAPI rejects an invalid body with 422 before this runs, so the store stays.
        return store.put_rules(body)

    @app.get("/decisions")
    def list_decisions(
        decision: Annotated[Literal["PAGAR", "ESCALAR", "FRENAR"] | None, Query()] = None,
    ) -> list[DecisionRecord]:
        records = list(store.decisions.values())
        if decision is None:
            return records
        return [item for item in records if item.decision == decision]

    @app.get("/decisions/{id}")
    def get_decision(id: str) -> DecisionRecord:
        found = store.get(id)
        if found is None:
            raise HTTPException(status_code=404, detail="not_found")
        return found

    @app.post("/invoices", status_code=201)
    async def post_invoice(
        file: Annotated[UploadFile, File()],
        invoice_id: Annotated[str, Form()],
        channel: Annotated[str, Form()],
        received_at: Annotated[str, Form()],
    ) -> DecisionRecord:
        try:
            meta = InvoiceMeta.model_validate(
                {
                    "invoice_id": invoice_id,
                    "channel": channel,
                    "received_at": received_at,
                }
            )
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
        content = await _read_capped(file)
        if content is None:
            raise HTTPException(status_code=422, detail="invalid_file_size")
        if store.has_invoice(meta.invoice_id):
            raise HTTPException(status_code=409, detail="duplicate_invoice")
        upload = InvoiceUpload(
            invoice_id=meta.invoice_id,
            channel=meta.channel,
            received_at=meta.received_at,
            content=content,
        )
        try:
            record = processor(upload)
        except InvoiceRejected as exc:
            raise HTTPException(status_code=422, detail=exc.detail) from exc
        try:
            return store.add_decision(record)
        except DuplicateDecisionError as exc:
            raise HTTPException(status_code=409, detail="duplicate_invoice") from exc

    @app.post("/decisions/{id}/approve")
    def approve(id: str, body: HumanDecisionBody) -> DecisionRecord:
        return _add_human_event(store, clock, id, body, "aprobada_humano")

    @app.post("/decisions/{id}/reject")
    def reject(id: str, body: HumanDecisionBody) -> DecisionRecord:
        return _add_human_event(store, clock, id, body, "rechazada_humano")

    @app.get("/metrics")
    def metrics() -> MetricsBody:
        # I9: no report → null. Do not invent unsafe_pay = 0.
        if metrics_reader is None:
            return MetricsBody(unsafe_pay=None, autonomy_pct=None, source="none")
        reading = metrics_reader()
        if reading is None:
            return MetricsBody(unsafe_pay=None, autonomy_pct=None, source="none")
        return MetricsBody(
            unsafe_pay=reading.unsafe_pay,
            autonomy_pct=reading.autonomy_pct,
            source="report",
        )

    @app.get("/openapi.json")
    def openapi_json() -> dict[str, object]:
        return app.openapi()

    return app


def _add_human_event(
    store: MemoryStore,
    clock: Clock,
    decision_id: str,
    body: HumanDecisionBody,
    action: HumanAction,
) -> DecisionRecord:
    # I2 / I4: append a human event. Do not rewrite decision or severity.
    found = store.get(decision_id)
    if found is None:
        raise HTTPException(status_code=404, detail="not_found")
    if found.decision != "ESCALAR":
        raise HTTPException(status_code=409, detail="not_escalated")
    event = HumanEvent(author=body.author, at=clock(), action=action, reason=body.reason)
    return store.add_human_event(decision_id, event)


async def _read_capped(file: UploadFile) -> bytes | None:
    """Read at most MAX_INVOICE_BYTES. Empty or larger uploads are rejected."""
    chunks: list[bytes] = []
    total = 0
    while True:
        block = await file.read(1024 * 1024)
        if not block:
            break
        total += len(block)
        if total > MAX_INVOICE_BYTES:
            return None
        chunks.append(block)
    if total < 1:
        return None
    return b"".join(chunks)
