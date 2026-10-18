"""R-perf / R3-new-text-operators-untested follow-up (code review on T3.2/T5.12).

Two kinds of regression covered here, both against the REAL `ingest_bytes`
(no mocks):

1. Quadratic regexes in `app/extraction/ingest.py` that scan unbounded on
   crafted input -- `_stream_filters`'s `<<(.*?)>>\\s*\\Z` over the whole
   `preceding` slice, and the literal-string `(...)` matching used for Tj /
   TJ-array text. Both must stay fast (< 1s) even on megabytes of adversarial
   input, while still extracting normally from a real document.
2. `_extract_text_operators` previously had no direct test coverage for TJ
   arrays, the `'`/`"` shorthand operators, or hex strings -- only plain
   `(text) Tj` was exercised via the existing PDF fixtures.
"""

from __future__ import annotations

import time
import zlib

import pytest
from app.extraction import IngestError, ingest_bytes


def _minimal_pdf(content_stream: bytes) -> bytes:
    """Build a tiny uncompressed single-page PDF around `content_stream`."""
    body = (
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n"
        + f"4 0 obj\n<< /Length {len(content_stream)} >>\nstream\n".encode()
        + content_stream
        + b"\nendstream\nendobj\n"
    )
    return b"%PDF-1.4\n" + body + b"%%EOF\n"


# --- perf: _stream_filters must not be quadratic on a huge `preceding` slice -----


def test_stream_filters_stays_fast_on_megabyte_of_angle_brackets() -> None:
    """A document with ~2 MB of bare `<<` (no closing `>>` anywhere) before the
    `stream` keyword must not make `_stream_filters`'s `<<(.*?)>>\\s*\\Z` search
    re-scan toward the end of the whole `preceding` slice for every one of the
    ~1M failed start positions -- that is what made it quadratic. No `/Filter`
    is ever found here, so the stream is treated as uncompressed (correct,
    conservative behavior), and its plain-text content must still come through.
    """
    junk = b"<<" * (1024 * 1024)  # ~2 MB, no closing ">>" anywhere in it
    content = b"BT (fast after padding) Tj ET"
    pdf = b"%PDF-1.4\n" + junk + b"\nstream\n" + content + b"\nendstream\nendobj\n%%EOF\n"

    start = time.perf_counter()
    result = ingest_bytes(pdf, channel="pdf_text")
    elapsed = time.perf_counter() - start

    assert elapsed < 1.0, f"took {elapsed:.3f}s, expected < 1s"
    assert result.text == "fast after padding"


def test_stream_filters_still_detects_flate_decode_in_a_normal_dict() -> None:
    """Correctness check alongside the perf fix above: a normal (small, real)
    stream dict's `/Filter /FlateDecode` must still be found and decoded."""
    content = b"BT (Normal dict still works) Tj ET"
    compressed = zlib.compress(content)
    body = (
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n"
        + b"4 0 obj\n<< /Filter /FlateDecode /Length "
        + str(len(compressed)).encode()
        + b" >>\nstream\n"
        + compressed
        + b"\nendstream\nendobj\n"
    )
    pdf = b"%PDF-1.4\n" + body + b"%%EOF\n"

    result = ingest_bytes(pdf, channel="pdf_text")

    assert result.text == "Normal dict still works"


# --- perf: literal `(...)` matching must not be quadratic on a run of "(" --------


def test_literal_extraction_stays_fast_on_two_megabytes_of_open_parens() -> None:
    pdf = _minimal_pdf(b"(" * (2 * 1024 * 1024))

    start = time.perf_counter()
    with pytest.raises(IngestError) as exc:
        ingest_bytes(pdf, channel="pdf_text")
    elapsed = time.perf_counter() - start

    assert elapsed < 1.0, f"took {elapsed:.3f}s, expected < 1s"
    assert exc.value.code == "illegible"


def test_normal_extraction_still_works_after_perf_fix() -> None:
    line = "Still works fine"
    pdf = _minimal_pdf(f"BT ({line}) Tj ET".encode("latin-1"))

    result = ingest_bytes(pdf, channel="pdf_text")

    assert result.text == line


# --- R3: TJ arrays, ' / " operators, and hex strings were previously untested ----


def test_tj_array_joins_pieces_in_document_convention() -> None:
    pdf = _minimal_pdf(b"BT [(Hel) -20 (lo)] TJ ET")

    result = ingest_bytes(pdf, channel="pdf_text")

    assert result.text == "Hello"


def test_single_quote_operator_extracts_literal() -> None:
    pdf = _minimal_pdf(b"BT (Quoted line) ' ET")

    result = ingest_bytes(pdf, channel="pdf_text")

    assert result.text == "Quoted line"


def test_double_quote_operator_extracts_literal() -> None:
    pdf = _minimal_pdf(b"BT (Double quoted) \" ET")

    result = ingest_bytes(pdf, channel="pdf_text")

    assert result.text == "Double quoted"


def test_ascii_hex_string_tj_decodes_to_text() -> None:
    # 48656C6C6F == "Hello" as ASCII hex.
    pdf = _minimal_pdf(b"BT <48656C6C6F> Tj ET")

    result = ingest_bytes(pdf, channel="pdf_text")

    assert result.text == "Hello"


def test_odd_length_hex_string_is_rejected_not_extracted() -> None:
    # 11 hex digits: odd length, not a valid byte sequence -- must be skipped
    # (fail closed), not raise or garble output. Pair with a normal literal so
    # the document still yields legible text overall.
    pdf = _minimal_pdf(b"BT (Still legible) Tj <48656C6C6> Tj ET")

    result = ingest_bytes(pdf, channel="pdf_text")

    assert result.text == "Still legible"
    assert "Hell" not in result.text


def test_non_ascii_hex_string_is_rejected_not_extracted() -> None:
    # 0001 decodes to bytes 0x00 0x01, outside the simple-ASCII range this
    # extractor supports (T5.12): must be skipped, not emit garbled text.
    pdf = _minimal_pdf(b"BT (Still legible) Tj <0001> Tj ET")

    result = ingest_bytes(pdf, channel="pdf_text")

    assert result.text == "Still legible"


def test_document_order_preserved_across_operator_kinds() -> None:
    content = (
        b"BT "
        b"(First) Tj "
        b"[(Sec) (ond)] TJ "
        b"<5468697264> Tj "
        b"(Fourth) ' "
        b"(Fifth) \" "
        b"ET"
    )
    pdf = _minimal_pdf(content)

    result = ingest_bytes(pdf, channel="pdf_text")

    assert result.text == "First\nSecond\nThird\nFourth\nFifth"
