"""T9.2 (D061) §8.5 — `POST /inbox` and the human actions on it, over HTTP.

Builds the app the same way every other API test does (`tests.api.support.
build_client`), so `/inbox` is exercised on the exact same app `/invoices`
runs on (same rate limiter, same `_decide_and_store_invoice`).
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from tests.api.support import USER_HEADERS, build_client

REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET_DIR = REPO_ROOT / "data" / "inbox" / "dev"


def _upload_eml(client, filename: str, *, headers: dict[str, str] | None = None):
    raw = (DATASET_DIR / filename).read_bytes()
    return client.post(
        "/inbox",
        files={"file": (filename, raw, "message/rfc822")},
        headers=headers if headers is not None else USER_HEADERS,
    )


def test_missing_user_id_matches_post_invoices_error() -> None:
    client, _store, _clock = build_client()
    bare = TestClient(client.app)
    invoices_response = bare.post("/invoices")
    inbox_response = _upload_eml(bare, "002_factura_en_cuerpo.eml", headers={})

    assert inbox_response.status_code == invoices_response.status_code == 401
    assert inbox_response.json()["detail"] == "missing_user_id"
    assert invoices_response.json()["detail"] == "missing_user_id"


def test_idempotent_by_message_id_no_second_decision() -> None:
    client, _store, _clock = build_client()

    first = _upload_eml(client, "002_factura_en_cuerpo.eml")
    assert first.status_code == 201
    first_body = first.json()
    assert first_body["classification"] == "es_factura"
    assert first_body["decision_id"] is not None

    # 010 carries the exact same Message-ID as 002 (§2/§8.5 resend scenario).
    second = _upload_eml(client, "010_reenvio_mismo_message_id.eml")
    assert second.status_code == 201
    second_body = second.json()
    assert second_body["id"] == first_body["id"]
    assert second_body["decision_id"] == first_body["decision_id"]

    decisions = client.get("/decisions", headers=USER_HEADERS).json()
    matching = [d for d in decisions if d["id"] == first_body["decision_id"]]
    assert len(matching) == 1  # no second decision was created for the resend


def test_more_than_five_attachments_goes_to_revision() -> None:
    client, _store, _clock = build_client()
    boundary = "X"
    parts = [f"--{boundary}", "Content-Type: text/plain; charset=utf-8", "", "cuerpo", ""]
    for i in range(6):
        parts += [
            f"--{boundary}",
            "Content-Type: text/plain",
            "Content-Transfer-Encoding: base64",
            f'Content-Disposition: attachment; filename="a{i}.txt"',
            "",
            "aGVsbG8=",
            "",
        ]
    parts.append(f"--{boundary}--")
    raw = (
        "Message-ID: <too-many@inbox.demo.test>\r\n"
        "From: x@example.test\r\n"
        "To: ap@acme.demo.test\r\n"
        "Subject: Muchos adjuntos\r\n"
        "Date: 2026-05-01\r\n"
        "MIME-Version: 1.0\r\n"
        f'Content-Type: multipart/mixed; boundary="{boundary}"\r\n'
        "\r\n" + "\n".join(parts)
    ).encode("utf-8")

    response = client.post(
        "/inbox", files={"file": ("many.eml", raw, "message/rfc822")}, headers=USER_HEADERS
    )
    assert response.status_code == 201
    body = response.json()
    assert body["classification"] == "revision"
    assert body["decision_id"] is None


def test_process_with_unknown_author_is_422() -> None:
    client, _store, _clock = build_client()
    upload = _upload_eml(client, "007_estado_cuenta_ambiguo.eml")
    assert upload.status_code == 201
    message_id = upload.json()["id"]

    response = client.post(
        f"/inbox/{message_id}/process",
        json={"author": "no-soy-aprobador@example.test"},
        headers=USER_HEADERS,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "unknown_approver"


def test_process_by_known_approver_creates_a_decision() -> None:
    client, _store, _clock = build_client()
    upload = _upload_eml(client, "007_estado_cuenta_ambiguo.eml")
    assert upload.status_code == 201
    body = upload.json()
    assert body["classification"] == "revision"
    assert body["decision_id"] is None
    message_id = body["id"]

    from tests.api.support import load_approver_emails

    approver = next(iter(load_approver_emails()))
    response = client.post(
        f"/inbox/{message_id}/process", json={"author": approver}, headers=USER_HEADERS
    )
    assert response.status_code == 200
    processed = response.json()
    assert processed["decision_id"] is not None
    assert any(e["action"] == "procesada_humano" for e in processed["events"])

    # Second attempt to process an already-decided message is rejected.
    again = client.post(
        f"/inbox/{message_id}/process", json={"author": approver}, headers=USER_HEADERS
    )
    assert again.status_code == 409


def test_dismiss_leaves_an_event_and_does_not_delete() -> None:
    client, _store, _clock = build_client()
    upload = _upload_eml(client, "004_boletin_bulk.eml")
    message_id = upload.json()["id"]

    response = client.post(
        f"/inbox/{message_id}/dismiss",
        json={"author": "quien-revisa@acme.demo.test", "reason": "Boletín, no es factura."},
        headers=USER_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == message_id
    assert any(e["action"] == "descartada_humano" for e in body["events"])

    fetched = client.get(f"/inbox/{message_id}", headers=USER_HEADERS).json()
    assert fetched["id"] == message_id  # still present, never deleted


def test_llm_es_factura_suggestion_never_creates_decision_id_without_process() -> None:
    """I2: even when the gray-zone LLM suggests `es_factura`, the record stays in
    `revision` with no `decision_id` until a human calls `process`.
    """
    client, _store, _clock = build_client()
    response = _upload_eml(client, "007_estado_cuenta_ambiguo.eml")
    body = response.json()
    assert body["classification"] in ("revision", "no_es_factura")
    assert body["decision_id"] is None
