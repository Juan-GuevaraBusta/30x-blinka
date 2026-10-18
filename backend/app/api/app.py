"""HTTP API. `decide()` is not called here: the injected processor already built the record."""

from __future__ import annotations

import hmac
import threading
from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from pydantic import ValidationError

from app.api.rate_limit import FixedWindowLimiter, RateLimitMiddleware
from app.api.schemas import (
    MAX_INVOICE_BYTES,
    ChainVerificationBody,
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

# T5.8 (D055): process-wide lock serializing ledger-read -> decide -> persist
# for POST /invoices (the only route that can settle PAGAR). Two concurrent
# invoices, each individually under `limits.per_period`, previously read the
# same prior-settled ledger, both decided PAGAR, and both persisted under
# distinct invoice_ids -- jointly exceeding the period limit. This mutex only
# serializes within one process: the deploy must run a single uvicorn worker
# (no `--workers`), it does not coordinate across workers or replicas.
# Production alternative, not implemented here (hackathon scope): a DB row
# lock (`SELECT ... FOR UPDATE`) or `SERIALIZABLE` isolation.
_INVOICE_LOCK = threading.Lock()


def create_app(
    store: MemoryStore,
    processor: Processor,
    *,
    clock: Clock,
    rate_limit: int,
    metrics_reader: MetricsReader | None = None,
    admin_api_key: str | None = None,
    approver_emails: frozenset[str] | None = None,
) -> FastAPI:
    """Build the app. Tests pass `store`, `processor`, `clock`, and `rate_limit`.

    T5.9 (D055): `admin_api_key` gates PUT /rules and approve/reject (fail-closed 503
    when unset). `approver_emails` is the static allowlist for `author`, normally
    `data/company.json`'s `approvers` values; it defaults to empty, so no author is
    accepted unless the caller passes the real set.
    """
    limiter = FixedWindowLimiter(rate_limit, clock)
    allowed_approvers = approver_emails if approver_emails is not None else frozenset()
    app = FastAPI(title="blinka-invoice-agent", openapi_url=None)
    app.add_middleware(RateLimitMiddleware, limiter=limiter)

    def _check_admin_key(
        x_admin_key: Annotated[str | None, Header(alias="X-Admin-Key")] = None,
    ) -> None:
        """Depends() runs during FastAPI's dependency-resolution phase, which
        completes before body fields are parsed into their Pydantic model
        (`request_body_to_args` in fastapi/dependencies/utils.py runs after the
        sub-dependency loop). Using this as a route dependency -- instead of a
        plain in-body check -- is what guarantees an unauthenticated caller gets
        401/503 even for a malformed body, never a 422 that leaks body-shape
        information before authentication (R3-auth-after-body-validation).
        """
        _require_admin_key(admin_api_key, x_admin_key)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/rules")
    def get_rules() -> RulesConfig:
        return store.rules

    @app.put("/rules")
    def put_rules(
        body: RulesConfig,
        _admin: None = Depends(_check_admin_key),
    ) -> RulesConfig:
        # `_admin` (Depends) runs before `body` is parsed, so an unauthenticated
        # caller gets 401/503, never 422 (R3-auth-after-body-validation). A valid
        # body that fails RulesConfig's own validators still rejects with 422.
        return store.put_rules(body)

    @app.get("/decisions")
    def list_decisions(
        decision: Annotated[Literal["PAGAR", "ESCALAR", "FRENAR"] | None, Query()] = None,
    ) -> list[DecisionRecord]:
        records = list(store.decisions.values())
        if decision is None:
            return records
        return [item for item in records if item.decision == decision]

    @app.get("/decisions/verify-chain")
    def verify_chain() -> ChainVerificationBody:
        """Public, read-only (T5.10, D055). Must stay registered before
        `/decisions/{id}` below -- Starlette matches routes in registration
        order, and `{id}` would otherwise swallow the literal "verify-chain"
        path and 404 as "not_found" instead of reaching this handler.
        """
        result = store.verify_chain()
        return ChainVerificationBody(
            ok=result.ok, length=result.length, first_broken_id=result.first_broken_id
        )

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
            return _decide_and_store_invoice(processor, store, upload)
        except InvoiceRejected as exc:
            raise HTTPException(status_code=422, detail=exc.detail) from exc
        except DuplicateDecisionError as exc:
            raise HTTPException(status_code=409, detail="duplicate_invoice") from exc

    @app.post("/decisions/{id}/approve")
    def approve(
        id: str,
        body: HumanDecisionBody,
        _admin: None = Depends(_check_admin_key),
    ) -> DecisionRecord:
        _require_known_approver(body.author, allowed_approvers)
        return _add_human_event(store, clock, id, body, "aprobada_humano")

    @app.post("/decisions/{id}/reject")
    def reject(
        id: str,
        body: HumanDecisionBody,
        _admin: None = Depends(_check_admin_key),
    ) -> DecisionRecord:
        _require_known_approver(body.author, allowed_approvers)
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


def _decide_and_store_invoice(
    processor: Processor, store: MemoryStore, upload: InvoiceUpload
) -> DecisionRecord:
    """Serialize decide + persist so a concurrent invoice always sees this one (T5.8)."""
    with _INVOICE_LOCK:
        record = processor(upload)
        return store.add_decision(record)


def _require_admin_key(configured: str | None, provided: str | None) -> None:
    """Fail-closed admin auth for mutating endpoints (T5.9, D055).

    No `ADMIN_API_KEY` in the environment -> 503, nobody can mutate even with a
    header. Configured and missing/wrong header -> 401 (no user session exists to
    distinguish "unauthenticated" from "authenticated without permission").
    """
    if not configured:
        raise HTTPException(status_code=503, detail="admin_key_not_configured")
    if not provided:
        raise HTTPException(status_code=401, detail="missing_admin_key")
    if not hmac.compare_digest(provided.encode("utf-8"), configured.encode("utf-8")):
        raise HTTPException(status_code=401, detail="invalid_admin_key")


def _require_known_approver(author: str, approver_emails: frozenset[str]) -> None:
    """`author` must be one of `data/company.json`'s `approvers` values (T5.9, D055)."""
    if author not in approver_emails:
        raise HTTPException(status_code=422, detail="unknown_approver")


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
