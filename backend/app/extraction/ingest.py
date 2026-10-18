"""Deterministic ingest: bytes by catalog channel to normalized text.

PNG / ``image`` channel: fail-closed ``illegible`` in T3.2 (no OCR). Roadmap cut for
reading corpus PNG is a future OCR task, not this module.
"""

from __future__ import annotations

import base64
import binascii
import re
import zlib
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

# Literal-string-then-operator: (text) Tj | (text) ' | (text) "
_TJ_PATTERN = re.compile(r"\((?:\\.|[^\\)])*\)\s*(?:Tj|'|\")")
_TJ_ARRAY_PATTERN = re.compile(r"\[((?:[^\[\]])*)\]\s*TJ")
_TJ_ARRAY_LITERAL = re.compile(r"\((?:\\.|[^\\)])*\)")
_HEX_STRING_OP = re.compile(r"<([0-9A-Fa-f\s]*)>\s*(?:Tj|'|\")")
_FILTER_PATTERN = re.compile(r"/Filter\s*(\[[^\]]*\]|/[A-Za-z0-9]+)")
_FILTER_NAME = re.compile(r"/([A-Za-z0-9]+)")
_ENCRYPT_SCAN = 8192
_MAX_DECOMPRESSED_BYTES = 5 * 1024 * 1024  # 5 MB decompression-bomb guard (T5.12)
# Whole-document budget: many streams just under the per-stream cap must not
# add up to hundreds of MB of decode + regex work in one request.
_MAX_DOCUMENT_DECODED_BYTES = 8 * 1024 * 1024
_KNOWN_FILTERS = frozenset({"FlateDecode", "ASCII85Decode"})


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

    lines: list[str] = []
    decoded_total = 0
    for raw, filters in _pdf_stream_chunks(doc):
        text = _decode_stream_filters(raw, filters)
        if text is None:
            # Unknown filter, corrupt payload, or decompression-bomb guard
            # tripped (T5.12): skip this stream, stay fail-closed overall.
            continue
        decoded_total += len(text)
        if decoded_total > _MAX_DOCUMENT_DECODED_BYTES:
            raise IngestError("illegible")
        lines.extend(_extract_text_operators(text))

    if not lines:
        raise IngestError("illegible")

    return "\n".join(lines)


def _pdf_stream_chunks(doc: str) -> list[tuple[bytes, tuple[str, ...]]]:
    """Yield (raw_bytes, filter_names) for every stream...endstream object.

    Byte-for-byte lossless: ``doc`` is a latin-1 decode of the original bytes
    (1:1 mapping over 0-255), so slicing text back with ``.encode("latin-1")``
    recovers the exact original bytes, including binary FlateDecode payloads.
    """
    chunks: list[tuple[bytes, tuple[str, ...]]] = []
    idx = 0
    prev_end = 0
    while True:
        marker = doc.find("stream\n", idx)
        if marker == -1:
            marker = doc.find("stream\r\n", idx)
            if marker == -1:
                return chunks
            content_start = marker + len("stream\r\n")
        else:
            content_start = marker + len("stream\n")

        # Some real-world writers omit the EOL before "endstream" (seen in
        # the T4.10 external smoke PDFs: "...~>endstream" with no newline),
        # so match the bare keyword rather than requiring "\nendstream".
        end = doc.find("endstream", content_start)
        if end == -1:
            return chunks

        preceding = doc[prev_end:marker]
        filters = _stream_filters(preceding)
        raw = doc[content_start:end].encode("latin-1", errors="replace")
        chunks.append((raw, filters))

        # Skip the whole keyword: resuming at end + 1 re-matched the "stream"
        # inside "endstream" and hid every later stream's /Filter.
        idx = end + len("endstream")
        prev_end = idx


def _stream_filters(preceding: str) -> tuple[str, ...]:
    """Read ``/Filter`` from the ``<< ... >>`` stream dict right before ``stream``."""
    dict_match = re.search(r"<<(.*?)>>\s*\Z", preceding, re.S)
    if not dict_match:
        return ()
    filter_match = _FILTER_PATTERN.search(dict_match.group(1))
    if not filter_match:
        return ()
    return tuple(_FILTER_NAME.findall(filter_match.group(1)))


def _decode_stream_filters(raw: bytes, filters: tuple[str, ...]) -> str | None:
    """Apply the declared filter chain; ``None`` means "skip this stream".

    Unknown filters (images, fonts, CMaps, CID programs, ...) and any decode
    failure are not errors on their own — the caller stays fail-closed only if
    *no* stream in the document yields readable text (T5.12).
    """
    if not filters:
        return raw.decode("latin-1", errors="replace")
    if not set(filters) <= _KNOWN_FILTERS:
        return None

    # The EOL before "endstream" is optional per spec and some real writers
    # omit it (T4.10 fixtures) while others keep it; strip it defensively so
    # base64.a85decode's strict "must end with ~>" check still matches.
    data = raw.rstrip(b" \t\r\n")
    try:
        for name in filters:
            if name == "ASCII85Decode":
                data = base64.a85decode(data, adobe=True)
            elif name == "FlateDecode":
                data = _flate_decompress(data)
    except (ValueError, binascii.Error, zlib.error):
        return None
    return data.decode("latin-1", errors="replace")


def _flate_decompress(raw: bytes) -> bytes:
    """Decompress with a hard cap so a tiny stream can't expand unbounded."""
    decompressor = zlib.decompressobj()
    out = bytearray()
    pending = raw
    while pending:
        budget = _MAX_DECOMPRESSED_BYTES + 1 - len(out)
        if budget <= 0:
            raise zlib.error("decompressed stream exceeds safety cap")
        out += decompressor.decompress(pending, budget)
        if len(out) > _MAX_DECOMPRESSED_BYTES:
            raise zlib.error("decompressed stream exceeds safety cap")
        pending = decompressor.unconsumed_tail
    out += decompressor.flush()
    if len(out) > _MAX_DECOMPRESSED_BYTES:
        raise zlib.error("decompressed stream exceeds safety cap")
    return bytes(out)


def _extract_text_operators(text: str) -> list[str]:
    """Extract Tj / ' / " literals, TJ arrays, and simple hex strings, in order."""
    found: list[tuple[int, str]] = []

    for match in _TJ_PATTERN.finditer(text):
        literal = match.group(0)
        inner = literal[1 : literal.rfind(")")]
        found.append((match.start(), _unescape_pdf_literal(inner)))

    for match in _TJ_ARRAY_PATTERN.finditer(text):
        pieces = _TJ_ARRAY_LITERAL.findall(match.group(1))
        joined = "".join(_unescape_pdf_literal(piece[1:-1]) for piece in pieces)
        if joined:
            found.append((match.start(), joined))

    for match in _HEX_STRING_OP.finditer(text):
        hex_digits = re.sub(r"\s+", "", match.group(1))
        if len(hex_digits) % 2 != 0:
            continue
        try:
            raw_bytes = bytes.fromhex(hex_digits)
        except ValueError:
            continue
        # "Simple" case only (T5.12): plain ASCII per byte. CID/custom-encoded
        # fonts (2-byte codes via a CMap unrelated to ASCII) stay fail-closed
        # instead of emitting garbled text.
        if raw_bytes and all(0x20 <= b <= 0x7E for b in raw_bytes):
            found.append((match.start(), raw_bytes.decode("ascii")))

    found.sort(key=lambda item: item[0])
    return [line for _, line in found]


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
