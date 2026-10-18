"""T3.2 — Ingest channels to normalized text (no OCR)."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.extraction import (
    IngestError,
    ingest_bytes,
    ingest_path,
    normalize_document_text,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
INVOICES = REPO_ROOT / "data" / "invoices"
FOOTER = "Documento ficticio. No representa a ninguna empresa real."


def test_normalize_document_text_line_endings() -> None:
    assert normalize_document_text("a\r\nb\r c") == "a\nb\n c"


def test_normalize_document_text_nfc() -> None:
    composed = "e\u0301"
    assert normalize_document_text(composed) == "\u00e9"


def test_ingest_chat_empty_after_normalize_raises_empty_text() -> None:
    with pytest.raises(IngestError) as exc:
        ingest_bytes(b"   \n", channel="chat")
    assert exc.value.code == "empty_text"
    assert str(exc.value) == "empty_text"


def test_ingest_pdf_non_pdf_bytes_unsupported_format() -> None:
    with pytest.raises(IngestError) as exc:
        ingest_bytes(b"not a pdf", channel="pdf_text")
    assert exc.value.code == "unsupported_format"


def test_ingest_pdf_empty_bytes_unsupported_format() -> None:
    with pytest.raises(IngestError) as exc:
        ingest_bytes(b"", channel="pdf_text")
    assert exc.value.code == "unsupported_format"


def test_minimal_inline_pdf_extracts_single_tj() -> None:
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
    assert result.channel == "pdf_text"


def test_dev_001_pdf_golden_substrings() -> None:
    path = REPO_ROOT / "data/invoices/dev/dev-001_normal_pay.pdf"
    result = ingest_path(path)
    assert result.channel == "pdf_text"
    assert "Beneficiario: Globex LLC" in result.text
    assert "Numero: INV-GX-2026-0105" in result.text
    assert "Total: 800 USD" in result.text
    assert FOOTER in result.text


def test_hold_001_pdf_english_lines() -> None:
    path = REPO_ROOT / "data/invoices/holdout/hold-001_normal_pay.pdf"
    result = ingest_path(path)
    assert "FROM: Globex LLC" in result.text
    assert "INVOICE: INV-H-GX-1" in result.text


def test_dev_003_email_body_and_subject() -> None:
    path = INVOICES / "dev" / "dev-003_normal_pay.eml"
    result = ingest_path(path)
    assert result.channel == "email"
    assert "Beneficiario: Globex LLC" in result.text
    assert FOOTER in result.text
    assert "From: billing@" not in result.text
    assert result.metadata.email_subject is not None
    assert "INV-GX-2026-0206" in result.metadata.email_subject


def test_dev_004_chat_full_file() -> None:
    path = INVOICES / "dev" / "dev-004_normal_pay.txt"
    result = ingest_path(path)
    assert result.channel == "chat"
    assert "adjunta factura INV-PP-2026-0209" in result.text
    assert "Beneficiario:" in result.text


def test_image_channel_illegible_without_reading_png() -> None:
    png_path = INVOICES / "dev" / "dev-002_normal_pay.png"
    png_bytes = png_path.read_bytes()
    with pytest.raises(IngestError) as exc:
        ingest_bytes(png_bytes, channel="image")
    assert exc.value.code == "illegible"

    with pytest.raises(IngestError) as exc2:
        ingest_path(png_path)
    assert exc2.value.code == "illegible"


def test_ingest_path_unknown_suffix_unsupported_format() -> None:
    with pytest.raises(IngestError) as exc:
        ingest_path(REPO_ROOT / "pyproject.toml")
    assert exc.value.code == "unsupported_format"


def test_source_files_do_not_contain_pagar_token() -> None:
    repo = Path(__file__).resolve().parents[2]
    for name in ("ingest.py", "text_normalize.py"):
        path = repo / "backend" / "app" / "extraction" / name
        assert "PAGAR" not in path.read_text(encoding="utf-8"), name
