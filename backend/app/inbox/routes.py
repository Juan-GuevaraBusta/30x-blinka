"""T9.2 (D061) §5 — `POST /inbox`, `GET /inbox`, `GET /inbox/{id}`,
`POST /inbox/{id}/process`, `POST /inbox/{id}/dismiss`.

`build_inbox_router` is called once from `app.api.app.create_app` (the only
edit to that file: one import and one `app.include_router(...)` call) so this
whole feature mounts onto the SAME FastAPI app, under the SAME global rate
limiter, and reuses the SAME `_decide_and_store_invoice` closure (lock +
`store.add_decision`) that `POST /invoices` uses -- no decision logic is
duplicated here.
"""

from __future__ import annotations

import base64
import binascii
from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Any, Protocol

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from app.api.schemas import InvoiceRejected, InvoiceUpload
from app.api.user_scope import require_user_id
from app.inbox.classifier import ClassificationResult, classify_email, limits_exceeded_result
from app.inbox.config import InboxClassifierConfig, default_inbox_classifier_config
from app.inbox.parser import (
    EmailParseError,
    ParsedEmail,
    looks_like_pdf,
    parse_eml_bytes,
    parse_json_email,
    select_document,
)
from app.inbox.schemas import InboxDismissBody, InboxEmailIn, InboxProcessBody
from app.inbox.store import InboxEvent, InboxMessage, InboxSignalBody, InboxStore
from app.models.domain import DecisionRecord

MAX_INBOX_RAW_BYTES = 40_000_000  # generous: up to 5 attachments x 5 MB, base64 overhead included

Clock = Callable[[], datetime]


class _Store(Protocol):
    rules: Any

    def list_active_agreements(self) -> list[Any]: ...
    def add_decision(self, record: DecisionRecord, owner_id: str) -> DecisionRecord: ...


DecideAndStoreInvoice = Callable[[Any, Any, InvoiceUpload, str], DecisionRecord]


def build_inbox_router(
    store: _Store,
    *,
    processor: Any,
    clock: Clock,
    approver_emails: frozenset[str],
    decide_and_store_invoice: DecideAndStoreInvoice,
    inbox_store: InboxStore | None = None,
    classifier_config: InboxClassifierConfig | None = None,
    llm: Any | None = None,
) -> APIRouter:
    inbox = inbox_store if inbox_store is not None else InboxStore()
    config = (
        classifier_config if classifier_config is not None else default_inbox_classifier_config()
    )

    router = APIRouter()

    def _sender_emails() -> frozenset[str]:
        emails: set[str] = set()
        for active in store.list_active_agreements():
            for raw in active.agreement.sender_emails:
                cleaned = raw.strip().lower()
                if cleaned:
                    emails.add(cleaned)
        return frozenset(emails)

    def _allowed_beneficiaries() -> tuple[str, ...]:
        return tuple(store.rules.allowed_beneficiaries)

    def _as_message_body(result: ClassificationResult) -> tuple[InboxSignalBody, ...]:
        return tuple(
            InboxSignalBody(id=s.id, points=s.points, evidence=s.evidence) for s in result.signals
        )

    def _attempt_deterministic_processing(
        message: InboxMessage, owner_id: str, document: tuple[str, bytes]
    ) -> InboxMessage:
        channel, content = document
        upload = InvoiceUpload(
            invoice_id=f"inbox-{message.id}",
            channel=channel,  # type: ignore[arg-type]
            received_at=clock(),
            content=content,
        )
        try:
            record = decide_and_store_invoice(processor, store, upload, owner_id)
        except InvoiceRejected:
            # Fail closed on the auto-route only: the email is still recorded as
            # `es_factura` (§3's deterministic result), simply without a decision
            # yet. A human can retry via POST /inbox/{id}/process.
            return message
        return message.model_copy(update={"decision_id": record.id})

    async def _parse_multipart(request: Request) -> ParsedEmail:
        form = await request.form()
        upload = form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(status_code=422, detail="missing_file")
        chunks: list[bytes] = []
        total = 0
        while True:
            block = await upload.read(1024 * 1024)
            if not block:
                break
            total += len(block)
            if total > MAX_INBOX_RAW_BYTES:
                raise HTTPException(status_code=422, detail="invalid_file_size")
            chunks.append(block)
        if total < 1:
            raise HTTPException(status_code=422, detail="invalid_file_size")
        raw = b"".join(chunks)
        try:
            return parse_eml_bytes(raw)
        except EmailParseError as exc:
            raise HTTPException(status_code=422, detail=exc.code) from exc

    async def _parse_json(request: Request) -> ParsedEmail:
        try:
            payload = await request.json()
        except Exception as exc:  # noqa: BLE001 - malformed JSON body
            raise HTTPException(status_code=422, detail="invalid_json") from exc
        try:
            body = InboxEmailIn.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc

        decoded_attachments: list[tuple[str, str, bytes]] = []
        for attachment in body.attachments:
            try:
                content = base64.b64decode(attachment.content_base64, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise HTTPException(status_code=422, detail="invalid_attachment_base64") from exc
            decoded_attachments.append((attachment.filename, attachment.content_type, content))

        return parse_json_email(
            message_id=body.message_id,
            from_addr=body.from_addr,
            to_addr=body.to_addr,
            subject=body.subject,
            date_raw=body.date,
            body_text=body.body_text,
            attachments_in=decoded_attachments,
        )

    @router.post("/inbox", status_code=201)
    async def post_inbox(
        request: Request,
        owner_id: Annotated[str, Depends(require_user_id)],
    ) -> InboxMessage:
        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" in content_type:
            parsed = await _parse_multipart(request)
        elif "application/json" in content_type:
            parsed = await _parse_json(request)
        else:
            raise HTTPException(status_code=422, detail="unsupported_content_type")

        existing = inbox.find_by_message_id(owner_id, parsed.message_id)
        if existing is not None:
            return existing

        document: tuple[Any, bytes]
        if parsed.too_many_attachments or parsed.oversized_attachment:
            result = limits_exceeded_result(
                too_many=parsed.too_many_attachments, oversized=parsed.oversized_attachment
            )
            document = ("email", parsed.raw_bytes)
        else:
            pdfs = tuple(a for a in parsed.attachments if looks_like_pdf(a))
            selected = select_document(parsed)
            result = classify_email(
                parsed,
                config=config,
                sender_emails=_sender_emails(),
                allowed_beneficiaries=_allowed_beneficiaries(),
                pdf_attachments=pdfs,
                document_ambiguous=selected.ambiguous,
                llm=llm,
            )
            document = (selected.channel, selected.content)

        message = InboxMessage(
            id=inbox.next_id(),
            owner_id=owner_id,
            message_id=parsed.message_id,
            from_addr=parsed.from_addr,
            subject=parsed.subject,
            received_at=clock(),
            classification=result.classification,
            score=result.score,
            signals=_as_message_body(result),
            reason=result.reason,
            classified_by=result.classified_by,
        )

        if result.classification == "es_factura" and result.classified_by == "rules":
            message = _attempt_deterministic_processing(message, owner_id, document)

        inbox.add(message, document=document)
        return message

    @router.get("/inbox")
    def list_inbox(owner_id: Annotated[str, Depends(require_user_id)]) -> list[InboxMessage]:
        return inbox.list_for_owner(owner_id)

    @router.get("/inbox/{id}")
    def get_inbox(owner_id: Annotated[str, Depends(require_user_id)], id: str) -> InboxMessage:
        found = inbox.get_for_owner(id, owner_id)
        if found is None:
            raise HTTPException(status_code=404, detail="not_found")
        return found

    @router.post("/inbox/{id}/process")
    def process_inbox(
        owner_id: Annotated[str, Depends(require_user_id)],
        id: str,
        body: InboxProcessBody,
    ) -> InboxMessage:
        # Same ordering as `approve`/`reject` in app.api.app: known-approver
        # check first (I2 -- only a human approver can route to the pipeline).
        if body.author not in approver_emails:
            raise HTTPException(status_code=422, detail="unknown_approver")
        found = inbox.get_for_owner(id, owner_id)
        if found is None:
            raise HTTPException(status_code=404, detail="not_found")
        if found.decision_id is not None:
            raise HTTPException(status_code=409, detail="already_processed")
        document = inbox.get_document(id)
        if document is None:
            raise HTTPException(status_code=409, detail="document_unavailable")
        channel, content = document
        upload = InvoiceUpload(
            invoice_id=f"inbox-{found.id}",
            channel=channel,  # type: ignore[arg-type]
            received_at=clock(),
            content=content,
        )
        try:
            record = decide_and_store_invoice(processor, store, upload, owner_id)
        except InvoiceRejected as exc:
            raise HTTPException(status_code=422, detail=exc.detail) from exc
        event = InboxEvent(
            author=body.author,
            at=clock(),
            action="procesada_humano",
            reason="Procesada como factura desde la bandeja.",
        )
        updated = found.model_copy(
            update={"decision_id": record.id, "events": (*found.events, event)}
        )
        return inbox.update(updated)

    @router.post("/inbox/{id}/dismiss")
    def dismiss_inbox(
        owner_id: Annotated[str, Depends(require_user_id)],
        id: str,
        body: InboxDismissBody,
    ) -> InboxMessage:
        found = inbox.get_for_owner(id, owner_id)
        if found is None:
            raise HTTPException(status_code=404, detail="not_found")
        event = InboxEvent(
            author=body.author, at=clock(), action="descartada_humano", reason=body.reason
        )
        updated = found.model_copy(update={"events": (*found.events, event)})
        return inbox.update(updated)

    return router
