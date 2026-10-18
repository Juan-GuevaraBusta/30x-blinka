"""Deterministic ingest: bytes by catalog channel to normalized text.

PNG / ``image`` channel: fail-closed ``illegible`` in T3.2 (no OCR). Roadmap cut for
reading corpus PNG is a future OCR task, not this module.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.extraction.text_normalize import normalize_document_text

IngestChannel = Literal["pdf_text", "image", "email", "chat"]

_CHANNELS: frozenset[str] = frozenset({"pdf_text", "image", "email", "chat"})

_SUFFIX_CHANNEL: dict[str, IngestChannel] = {
    ".pdf": "pdf_text",
    ".png": "image",
    ".eml": "email",
    ".txt": "chat",
}

_TJ_PATTERN = re.compile(r"\((?:\\.|[^\\)])*\)\s*Tj")
_ENCRYPT_SCAN = 8192


class IngestMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_path: str | None = None
    content_type: str | None = None
    email_subject: str | None = None


class IngestResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    channel: IngestChannel
    text: str = Field(min_length=1)
    metadata: IngestMetadata


class IngestError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def ingest_bytes(
    data: bytes,
    *,
    channel: IngestChannel,
    source_path: str | None = None,
) -> IngestResult:
    if channel not in _CHANNELS:
        raise IngestError("unsupported_channel")

    metadata = IngestMetadata(source_path=source_path)

    if channel == "image":
        raise IngestError("illegible")

    if channel == "pdf_text":
        raw = _ingest_pdf_text(data)
        metadata = metadata.model_copy(update={"content_type": "application/pdf"})
    elif channel == "email":
        raw, subject = _ingest_email_raw(data)
        metadata = metadata.model_copy(
            update={"content_type": "message/rfc822", "email_subject": subject}
        )
    else:
        raw = _ingest_chat(data)
        metadata = metadata.model_copy(update={"content_type": "text/plain"})

    text = normalize_document_text(raw)
    if not text.strip():
        raise IngestError("empty_text")

    return IngestResult(channel=channel, text=text, metadata=metadata)


def ingest_path(path: Path, *, channel: IngestChannel | None = None) -> IngestResult:
    resolved = channel
    if resolved is None:
        suffix = path.suffix.lower()
        if suffix not in _SUFFIX_CHANNEL:
            raise IngestError("unsupported_format")
        resolved = _SUFFIX_CHANNEL[suffix]

    data = path.read_bytes()
    return ingest_bytes(data, channel=resolved, source_path=str(path))


def _ingest_pdf_text(data: bytes) -> str:
    if not data.startswith(b"%PDF-"):
        raise IngestError("unsupported_format")
    if b"/Encrypt" in data[:_ENCRYPT_SCAN]:
        raise IngestError("unsupported_format")

    doc = data.decode("latin-1", errors="replace")
    stream = _pdf_content_stream(doc)
    if not stream:
        raise IngestError("illegible")

    lines: list[str] = []
    for match in _TJ_PATTERN.finditer(stream):
        literal = match.group(0)
        inner = literal[1 : literal.rfind(")")]
        lines.append(_unescape_pdf_literal(inner))

    if not lines:
        raise IngestError("illegible")

    return "\n".join(lines)


def _pdf_content_stream(doc: str) -> str:
    idx = 0
    while True:
        marker = doc.find("stream\n", idx)
        if marker == -1:
            marker = doc.find("stream\r\n", idx)
            if marker == -1:
                return ""
            content_start = marker + len("stream\r\n")
        else:
            content_start = marker + len("stream\n")

        end = doc.find("\nendstream", content_start)
        if end == -1:
            end = doc.find("\rendstream", content_start)
            if end == -1:
                return ""
        chunk = doc[content_start:end]
        if "Tj" in chunk:
            return chunk
        idx = end + 1


def _unescape_pdf_literal(s: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        i += 1
        if i >= len(s):
            out.append("\\")
            break
        nxt = s[i]
        if nxt in "\\()":
            out.append(nxt)
            i += 1
        elif nxt.isdigit():
            digits = nxt
            i += 1
            for _ in range(2):
                if i < len(s) and s[i].isdigit():
                    digits += s[i]
                    i += 1
                else:
                    break
            out.append(chr(int(digits, 8)))
        else:
            out.append("\\")
    return "".join(out)


def _ingest_email_raw(data: bytes) -> tuple[str, str | None]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise IngestError("corrupt_file") from None

    subject: str | None = None
    for sep in ("\r\n\r\n", "\n\n"):
        if sep in text:
            headers, body = text.split(sep, 1)
            subject = _parse_subject(headers)
            return body, subject

    headers, body = text, ""
    subject = _parse_subject(headers) if "\n" in headers else None
    return body, subject


def _parse_subject(headers: str) -> str | None:
    for line in headers.splitlines():
        if line.lower().startswith("subject:"):
            return line.split(":", 1)[1].strip()
    return None


def _ingest_chat(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise IngestError("corrupt_file") from None
