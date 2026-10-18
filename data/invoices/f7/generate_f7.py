#!/usr/bin/env python3
"""T7.6 — Deterministic synthetic invoice file generator for the f7 split (stdlib only).

Mirrors ``data/invoices/generate.py`` (T1.6) but only needs txt, eml and
PDF-of-text channels (no images or scanned documents in f7). Reads
``data/invoices/f7/catalog.json`` and (re)writes the files it lists; running it
twice in a row produces byte-identical output (see
``backend/tests/test_f7_corpus.py``).
"""

from __future__ import annotations

import json
from pathlib import Path

FOOTER = "Documento ficticio. No representa a ninguna empresa real."
REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = Path(__file__).resolve().parent / "catalog.json"


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _format_amount(amount: float | int, currency: str) -> str:
    if isinstance(amount, float) and amount.is_integer():
        amount = int(amount)
    return f"{amount} {currency}"


def _body_lines(entry: dict) -> list[str]:
    lines = [
        f"Split: {entry['split']} / feature {entry['feature']} / caso {entry['case']}",
        f"Beneficiario: {entry['beneficiary']}",
        f"Numero: {entry['invoice_number']}",
        f"Total: {_format_amount(entry['amount'], entry['currency'])}",
        f"Vence: {entry['due_date']}",
        f"Departamento: {entry['department']}",
        f"Destinatario: {entry['recipient']}",
    ]
    if entry.get("manual_block"):
        lines.append("Bloqueo manual de prueba: si")
    note = entry.get("notes")
    if note:
        lines.append(f"Nota: {note}")
    lines.append(FOOTER)
    return lines


def _build_txt(lines: list[str]) -> bytes:
    return ("\n".join(lines) + "\n").encode("utf-8")


def _build_eml(entry: dict, lines: list[str]) -> bytes:
    beneficiary = entry["beneficiary"]
    subject = f"Factura {entry['invoice_number']} de {beneficiary} (f7)"
    body = "\n".join(lines) + "\n"
    sender_slug = beneficiary.lower().replace(" ", "-").replace(".", "")[:24]
    eml = (
        f"From: billing@{sender_slug}.demo.test\r\n"
        f"To: ap@acme.demo.test\r\n"
        f"Subject: {subject}\r\n"
        f"Date: {entry['received_at'][:10]}\r\n"
        f"MIME-Version: 1.0\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"\r\n"
        f"{body}"
    )
    return eml.encode("utf-8")


def _build_chat(entry: dict, lines: list[str]) -> bytes:
    stamp = entry["received_at"][:10] + " 10:15"
    header = f"[{stamp}] {entry['beneficiary']}: adjunta factura {entry['invoice_number']}"
    text = header + "\n" + "\n".join(lines) + "\n"
    return text.encode("utf-8")


def _build_pdf(lines: list[str]) -> bytes:
    y_start = 750
    y_step = 16
    parts = ["BT", "/F1 12 Tf"]
    y = y_start
    for line in lines:
        parts.append(f"1 0 0 1 72 {y} Tm ({_pdf_escape(line)}) Tj")
        y -= y_step
    parts.append("ET")
    stream = "\n".join(parts).encode("latin-1", errors="replace")

    objects: list[bytes] = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> >>\nendobj\n"
        ),
        (
            f"4 0 obj\n<< /Length {len(stream)} >>\nstream\n".encode()
            + stream
            + b"\nendstream\nendobj\n"
        ),
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]

    header = b"%PDF-1.4\n"
    body = b"".join(objects)
    offsets = [0]
    pos = len(header)
    for obj in objects:
        offsets.append(pos)
        pos += len(obj)

    xref_lines = [f"0 {len(offsets)}\n0000000000 65535 f \n"]
    for off in offsets[1:]:
        xref_lines.append(f"{off:010d} 00000 n \n")
    xref = b"xref\n" + "".join(xref_lines).encode()
    trailer = (
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{len(header) + len(body)}\n%%EOF\n"
    ).encode()
    return header + body + xref + trailer


def _render_entry(entry: dict) -> bytes:
    lines = _body_lines(entry)
    channel = entry["channel"]
    if channel == "txt":
        return _build_txt(lines)
    if channel == "email":
        return _build_eml(entry, lines)
    if channel == "chat":
        return _build_chat(entry, lines)
    if channel == "pdf_text":
        return _build_pdf(lines)
    raise ValueError(f"Unknown f7 channel: {channel}")


def main() -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    for entry in catalog:
        out = REPO_ROOT / entry["path"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(_render_entry(entry))


if __name__ == "__main__":
    main()
