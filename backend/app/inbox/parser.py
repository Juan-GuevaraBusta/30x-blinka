"""T9.2 (D061) §2 — MIME email parsing (`email` stdlib, `policy.default`).

No network, no execution of HTML/scripts: HTML bodies are reduced to plain text
with a small tag-stripping regex (`_strip_html`), never rendered or fetched.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parseaddr
from html import unescape
from typing import Literal

MAX_ATTACHMENTS = 5
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
DocumentChannel = Literal["pdf_text", "email"]


class EmailParseError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class InboxAttachment:
    filename: str
    content_type: str
    content: bytes


@dataclass(frozen=True)
class ParsedEmail:
    """Everything the classifier and the document-selection step need.

    `raw_bytes` is the full original message (or, for the JSON input shape, a
    synthesized RFC 822-ish rendering of it) -- it is what gets fed to the
    existing invoice pipeline's `email` channel when there is no single PDF
    attachment to use instead (§3).
    """

    message_id: str
    from_addr: str
    to_addr: str
    subject: str
    date_raw: str | None
    body_text: str
    attachments: tuple[InboxAttachment, ...]
    list_unsubscribe: bool
    precedence_bulk: bool
    auto_submitted: bool
    raw_bytes: bytes
    too_many_attachments: bool
    oversized_attachment: bool


@dataclass(frozen=True)
class SelectedDocument:
    """§3: the single document that would enter the invoice pipeline."""

    channel: DocumentChannel
    content: bytes
    ambiguous: bool


_TAG_BLOCK = re.compile(r"(?is)<(script|style)[^>]*>.*?</\1>")
_TAG = re.compile(r"(?s)<[^>]+>")
_WS = re.compile(r"[ \t]+")


def _strip_html(html: str) -> str:
    """Plain text from HTML without executing or fetching anything."""
    text = _TAG_BLOCK.sub(" ", html)
    text = _TAG.sub(" ", text)
    text = unescape(text)
    text = _WS.sub(" ", text)
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def looks_like_pdf(attachment: InboxAttachment) -> bool:
    return (
        attachment.content_type == "application/pdf"
        or attachment.filename.lower().endswith(".pdf")
    )


def sender_email_address(from_addr: str) -> str:
    """Bare address from a `"Name" <addr>` header, lowercased."""
    _, addr = parseaddr(from_addr)
    return addr.strip().lower()


def sender_domain(from_addr: str) -> str:
    addr = sender_email_address(from_addr)
    return addr.rsplit("@", 1)[1] if "@" in addr else ""


def _extract_attachments(msg: EmailMessage) -> list[InboxAttachment]:
    attachments: list[InboxAttachment] = []
    for part in msg.iter_attachments():
        filename = part.get_filename() or "attachment"
        content_type = part.get_content_type()
        try:
            payload = part.get_content()
        except Exception:  # noqa: BLE001 - fail closed to raw bytes, never crash the parse
            payload = part.get_payload(decode=True) or b""
        if isinstance(payload, str):
            payload = payload.encode("utf-8", errors="replace")
        if not isinstance(payload, bytes):
            payload = bytes(payload)
        attachments.append(
            InboxAttachment(filename=filename, content_type=content_type, content=payload)
        )
    return attachments


def _extract_body_text(msg: EmailMessage) -> str:
    body_part = msg.get_body(preferencelist=("plain", "html"))
    if body_part is None:
        return ""
    try:
        content = body_part.get_content()
    except Exception:  # noqa: BLE001 - malformed charset etc.; fail closed to empty body
        return ""
    if not isinstance(content, str):
        return ""
    if body_part.get_content_type() == "text/html":
        return _strip_html(content)
    return content


def parse_eml_bytes(raw: bytes) -> ParsedEmail:
    """Multipart `.eml` upload (§2): headers, text body, attachments."""
    try:
        msg = BytesParser(policy=policy.default).parsebytes(raw)
    except Exception as exc:  # noqa: BLE001 - any parse failure is fail-closed, not a 500
        raise EmailParseError("corrupt_email") from exc
    if not isinstance(msg, EmailMessage):
        raise EmailParseError("corrupt_email")

    message_id = (msg.get("Message-ID") or "").strip()
    if not message_id:
        message_id = "sha256:" + hashlib.sha256(raw).hexdigest()

    precedence = (msg.get("Precedence") or "").strip().lower()
    auto_submitted = (msg.get("Auto-Submitted") or "").strip().lower()

    attachments = _extract_attachments(msg)
    too_many = len(attachments) > MAX_ATTACHMENTS
    oversized = any(len(a.content) > MAX_ATTACHMENT_BYTES for a in attachments)

    return ParsedEmail(
        message_id=message_id,
        from_addr=(msg.get("From") or "").strip(),
        to_addr=(msg.get("To") or "").strip(),
        subject=(msg.get("Subject") or "").strip(),
        date_raw=msg.get("Date"),
        body_text=_extract_body_text(msg),
        attachments=tuple(attachments),
        list_unsubscribe=msg.get("List-Unsubscribe") is not None,
        precedence_bulk=precedence == "bulk",
        auto_submitted=auto_submitted not in ("", "no"),
        raw_bytes=raw,
        too_many_attachments=too_many,
        oversized_attachment=oversized,
    )


def select_document(parsed: ParsedEmail) -> SelectedDocument:
    """§3: the single PDF attachment, or else the email body (channel `email`).

    More than one PDF candidate is ambiguous -- the caller forces `revision`
    for that case, but a document is still returned (the first PDF) so a
    human who later clicks "Procesar como factura" has something to process.
    """
    pdfs = [a for a in parsed.attachments if looks_like_pdf(a)]
    if pdfs:
        return SelectedDocument(
            channel="pdf_text", content=pdfs[0].content, ambiguous=len(pdfs) > 1
        )
    return SelectedDocument(channel="email", content=parsed.raw_bytes, ambiguous=False)


def parse_json_email(
    *,
    message_id: str | None,
    from_addr: str,
    to_addr: str,
    subject: str,
    date_raw: str | None,
    body_text: str,
    attachments_in: list[tuple[str, str, bytes]],
) -> ParsedEmail:
    """§2 JSON input shape: already-structured fields, no MIME to parse.

    `attachments_in` is `(filename, content_type, decoded_bytes)`; base64
    decoding happens at the API boundary (invalid base64 is a 422, not a parse
    error here). `raw_bytes` is a synthesized RFC 822-ish rendering so the
    downstream invoice pipeline still sees the same `email` channel shape it
    would see from a real `.eml` upload (§3).
    """
    attachments = tuple(
        InboxAttachment(filename=name, content_type=ctype, content=content)
        for name, ctype, content in attachments_in
    )
    too_many = len(attachments) > MAX_ATTACHMENTS
    oversized = any(len(a.content) > MAX_ATTACHMENT_BYTES for a in attachments)

    header_lines = [
        f"From: {from_addr}",
        f"To: {to_addr}",
        f"Subject: {subject}",
    ]
    if date_raw:
        header_lines.append(f"Date: {date_raw}")
    if message_id:
        header_lines.append(f"Message-ID: {message_id}")
    header_lines += ["MIME-Version: 1.0", "Content-Type: text/plain; charset=utf-8"]
    raw_text = "\r\n".join(header_lines) + "\r\n\r\n" + body_text
    raw_bytes = raw_text.encode("utf-8")

    resolved_message_id = (message_id or "").strip()
    if not resolved_message_id:
        content_digest = hashlib.sha256(
            (from_addr + "\n" + subject + "\n" + body_text).encode("utf-8")
            + b"".join(c for _, _, c in attachments_in)
        ).hexdigest()
        resolved_message_id = f"sha256:{content_digest}"

    return ParsedEmail(
        message_id=resolved_message_id,
        from_addr=from_addr,
        to_addr=to_addr,
        subject=subject,
        date_raw=date_raw,
        body_text=body_text,
        attachments=attachments,
        list_unsubscribe=False,
        precedence_bulk=False,
        auto_submitted=False,
        raw_bytes=raw_bytes,
        too_many_attachments=too_many,
        oversized_attachment=oversized,
    )
