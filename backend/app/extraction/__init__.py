"""Invoice and contract extraction (ingest T3.2; extract T3.3; contracts T3.4)."""

from backend.app.extraction.extract import (
    EXTRACTOR_SYSTEM_PROMPT,
    ExtractError,
    extract_document,
)
from backend.app.extraction.ingest import (
    IngestChannel,
    IngestError,
    IngestMetadata,
    IngestResult,
    ingest_bytes,
    ingest_path,
)
from backend.app.extraction.text_normalize import normalize_document_text

from .contracts import (
    CONTRACT_EXTRACTOR_SYSTEM_PROMPT,
    ContractLookupError,
    ContractRecord,
    lookup_contract,
    parse_confirmed_marker,
)

__all__ = [
    "CONTRACT_EXTRACTOR_SYSTEM_PROMPT",
    "ContractLookupError",
    "ContractRecord",
    "EXTRACTOR_SYSTEM_PROMPT",
    "ExtractError",
    "extract_document",
    "lookup_contract",
    "parse_confirmed_marker",
    "IngestChannel",
    "IngestError",
    "IngestMetadata",
    "IngestResult",
    "ingest_bytes",
    "ingest_path",
    "normalize_document_text",
]
