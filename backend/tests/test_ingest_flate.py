"""T5.12 — decode FlateDecode (and ASCII85Decode+FlateDecode) PDF content streams.

Real-world PDFs compress their content stream; `_pdf_content_stream` only ever
read raw uncompressed bytes, so every normal PDF hit `IngestError("illegible")`.
These tests exercise the REAL ingest (no mocks) against the two external smoke
PDFs plus synthetic/adversarial fixtures built in-test.
"""

from __future__ import annotations

import base64
import zlib
from pathlib import Path

import pytest
from app.extraction import IngestError, ingest_bytes, ingest_path

REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_EXTERNAL = REPO_ROOT / "data" / "invoices" / "smoke-external"


def _flate_pdf(content_stream: bytes, *, filter_token: bytes = b"/FlateDecode") -> bytes:
    """Build a tiny single-page PDF whose content stream is FlateDecode-compressed."""
    compressed = zlib.compress(content_stream)
    body = (
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n"
        + b"4 0 obj\n<< /Filter "
        + filter_token
        + f" /Length {len(compressed)} >>\nstream\n".encode()
        + compressed
        + b"\nendstream\nendobj\n"
    )
    return b"%PDF-1.4\n" + body + b"%%EOF\n"


def test_external_smoke_01_pdf_extracts_real_text() -> None:
    path = SMOKE_EXTERNAL / "external-smoke-01.pdf"
    assert path.is_file(), f"missing fixture {path}"
    result = ingest_path(path)
    assert result.channel == "pdf_text"
    # Confirmed by manual zlib/base64 inspection of the real compressed stream.
    assert "QPPIDXHR773003856" in result.text
    assert "Nr.196470" in result.text


def test_external_smoke_02_pdf_extracts_real_text() -> None:
    path = SMOKE_EXTERNAL / "external-smoke-02.pdf"
    assert path.is_file(), f"missing fixture {path}"
    result = ingest_path(path)
    assert result.channel == "pdf_text"
    assert "WKVJRZWQ936435371" in result.text
    assert "Nr.122974" in result.text


def test_synthetic_flate_pdf_bare_filter_extracts_tj() -> None:
    line = "Flate hello"
    stream = f"BT /F1 12 Tf 1 0 0 1 72 700 Tm ({line}) Tj ET".encode("latin-1")
    pdf = _flate_pdf(stream, filter_token=b"/FlateDecode")
    result = ingest_bytes(pdf, channel="pdf_text")
    assert result.text == line


def test_synthetic_flate_pdf_array_filter_extracts_tj() -> None:
    line = "Flate array hello"
    stream = f"BT /F1 12 Tf 1 0 0 1 72 700 Tm ({line}) Tj ET".encode("latin-1")
    pdf = _flate_pdf(stream, filter_token=b"[/FlateDecode]")
    result = ingest_bytes(pdf, channel="pdf_text")
    assert result.text == line


def test_synthetic_ascii85_then_flate_pdf_extracts_tj() -> None:
    line = "Ascii85 then flate"
    stream = f"BT /F1 12 Tf 1 0 0 1 72 700 Tm ({line}) Tj ET".encode("latin-1")
    compressed = zlib.compress(stream)
    a85 = base64.a85encode(compressed, adobe=True)
    filter_entry = "/Filter [ /ASCII85Decode /FlateDecode ]"
    body = (
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n"
        + f"4 0 obj\n<< {filter_entry} /Length {len(a85)} >>\nstream\n".encode()
        + a85
        + b"\nendstream\nendobj\n"
    )
    pdf = b"%PDF-1.4\n" + body + b"%%EOF\n"
    result = ingest_bytes(pdf, channel="pdf_text")
    assert result.text == line


def test_corrupted_flate_stream_stays_illegible() -> None:
    # _flate_pdf would re-compress its input, so corrupt the already-compressed
    # payload directly to force a deterministic zlib.error on decode.
    good = _flate_pdf(b"BT (irrelevant) Tj ET")
    marker = b"stream\n"
    start = good.find(marker) + len(marker)
    end = good.find(b"\nendstream", start)
    corrupted = good[:start] + (good[start:end][:-5] + b"\x00\x00\x00\x00\x00") + good[end:]
    with pytest.raises(IngestError) as exc:
        ingest_bytes(corrupted, channel="pdf_text")
    assert exc.value.code == "illegible"


def test_decompression_bomb_guard_stays_illegible() -> None:
    huge = b"A" * (20 * 1024 * 1024)  # 20 MB, highly compressible
    bomb = _flate_pdf(huge)
    with pytest.raises(IngestError) as exc:
        ingest_bytes(bomb, channel="pdf_text")
    assert exc.value.code == "illegible"


def test_uncompressed_pdf_path_unaffected() -> None:
    line = "Hello ingest"
    stream = f"BT /F1 12 Tf 1 0 0 1 72 700 Tm ({line}) Tj ET".encode("latin-1")
    body = (
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n"
        + f"4 0 obj\n<< /Length {len(stream)} >>\nstream\n".encode()
        + stream
        + b"\nendstream\nendobj\n"
    )
    pdf = b"%PDF-1.4\n" + body + b"%%EOF\n"
    result = ingest_bytes(pdf, channel="pdf_text")
    assert result.text == line


def _flate_pdf_multi(streams: list[bytes]) -> bytes:
    """Build a PDF with one FlateDecode content stream object per entry."""
    body = b""
    for n, content in enumerate(streams, start=4):
        compressed = zlib.compress(content)
        body += (
            f"{n} 0 obj\n<< /Filter /FlateDecode /Length {len(compressed)} >>\nstream\n".encode()
            + compressed
            + b"\nendstream\nendobj\n"
        )
    return b"%PDF-1.4\n" + body + b"%%EOF\n"


def test_every_flate_stream_is_decoded_not_only_the_first() -> None:
    pdf = _flate_pdf_multi([b"BT (first part) Tj ET", b"BT (second part) Tj ET"])
    text = ingest_bytes(pdf, channel="pdf_text").text
    assert "first part" in text
    assert "second part" in text


def test_document_level_decompression_cap_stays_illegible() -> None:
    # Each stream stays under the per-stream cap; together they exceed the
    # document-level budget, so the whole document must fail closed.
    chunk = b"BT (A) Tj ET\n" * (4 * 1024 * 1024 // 13)
    pdf = _flate_pdf_multi([chunk, chunk, chunk])
    with pytest.raises(IngestError) as exc:
        ingest_bytes(pdf, channel="pdf_text")
    assert exc.value.code == "illegible"
