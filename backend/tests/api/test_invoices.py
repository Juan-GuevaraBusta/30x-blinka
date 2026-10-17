"""POST /invoices uses the injected processor. No sockets."""

from __future__ import annotations

from app.api.schemas import InvoiceRejected, InvoiceUpload
from app.models.domain import DecisionRecord
from tests.api.support import build_client, make_record

_META = {
    "invoice_id": "INV-0042",
    "channel": "pdf_text",
    "received_at": "2026-03-04T10:15:00Z",
}


def _post(
    client,
    *,
    content: bytes | None = b"%PDF-demo",
    data: dict[str, str] | None = None,
    omit_file: bool = False,
):
    fields = dict(_META)
    if data:
        fields.update(data)
    if omit_file or content is None:
        return client.post("/invoices", data=fields)
    return client.post(
        "/invoices",
        data=fields,
        files={"file": ("invoice.pdf", content, "application/pdf")},
    )


def test_post_invoice_returns_processor_record() -> None:
    expected = make_record()
    seen: list[InvoiceUpload] = []

    def processor(upload: InvoiceUpload) -> DecisionRecord:
        seen.append(upload)
        return expected

    client, store, _clock = build_client(processor=processor)

    response = _post(client, content=b"%PDF-demo")

    assert response.status_code == 201
    assert response.json()["id"] == expected.id
    assert response.json()["decision"] == "ESCALAR"
    assert response.json()["invoice_id"] == "INV-0042"
    assert store.decisions[expected.id] is expected
    assert len(seen) == 1
    assert seen[0].content == b"%PDF-demo"
    assert seen[0].invoice_id == "INV-0042"
    assert seen[0].channel == "pdf_text"
    assert seen[0].received_at.tzinfo is not None


def test_duplicate_invoice_returns_409_without_second_call() -> None:
    calls = {"n": 0}

    def processor(upload: InvoiceUpload) -> DecisionRecord:
        calls["n"] += 1
        return make_record(invoice_id=upload.invoice_id)

    client, store, _clock = build_client(processor=processor)

    first = _post(client)
    second = _post(client)

    assert first.status_code == 201
    assert second.status_code == 409
    assert calls["n"] == 1
    assert len(store.decisions) == 1


def test_empty_file_returns_422_without_calling_processor() -> None:
    calls = {"n": 0}

    def processor(_upload: InvoiceUpload) -> DecisionRecord:
        calls["n"] += 1
        return make_record()

    client, store, _clock = build_client(processor=processor)

    response = _post(client, content=b"")

    assert response.status_code == 422
    assert calls["n"] == 0
    assert store.decisions == {}


def test_oversize_file_returns_422() -> None:
    calls = {"n": 0}

    def processor(_upload: InvoiceUpload) -> DecisionRecord:
        calls["n"] += 1
        return make_record()

    client, _store, _clock = build_client(processor=processor)

    response = _post(client, content=b"x" * 2_000_001)

    assert response.status_code == 422
    assert calls["n"] == 0


def test_max_file_size_is_accepted() -> None:
    client, store, _clock = build_client()

    response = _post(client, content=b"x" * 2_000_000)

    assert response.status_code == 201
    assert len(store.decisions) == 1


def test_invoice_id_with_space_returns_422() -> None:
    calls = {"n": 0}

    def processor(_upload: InvoiceUpload) -> DecisionRecord:
        calls["n"] += 1
        return make_record()

    client, _store, _clock = build_client(processor=processor)

    response = _post(client, data={"invoice_id": "INV 0042"})

    assert response.status_code == 422
    assert calls["n"] == 0


def test_naive_received_at_returns_422() -> None:
    calls = {"n": 0}

    def processor(_upload: InvoiceUpload) -> DecisionRecord:
        calls["n"] += 1
        return make_record()

    client, _store, _clock = build_client(processor=processor)

    response = _post(client, data={"received_at": "2026-03-04T10:15:00"})

    assert response.status_code == 422
    assert calls["n"] == 0


def test_unknown_channel_returns_422() -> None:
    client, _store, _clock = build_client()

    response = _post(client, data={"channel": "fax"})

    assert response.status_code == 422


def test_processor_domain_error_returns_422_without_traceback() -> None:
    def processor(_upload: InvoiceUpload) -> DecisionRecord:
        raise InvoiceRejected("rejected")

    client, store, _clock = build_client(processor=processor)

    response = _post(client)

    assert response.status_code == 422
    assert response.json()["detail"] == "rejected"
    assert "Traceback" not in response.text
    assert "sk-" not in response.text
    assert store.decisions == {}
