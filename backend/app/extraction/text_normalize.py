"""Pure document text normalization for ingest and rules."""

from __future__ import annotations

import unicodedata


def normalize_document_text(raw: str) -> str:
    """Replace CRLF/CR with LF, apply Unicode NFC, rstrip trailing whitespace only."""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFC", text)
    return text.rstrip()
