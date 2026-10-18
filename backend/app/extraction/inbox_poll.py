"""T9.2 (D061) §2 — Local inbox poll for the demo: no mailbox, no network.

    python -m app.extraction.inbox_poll --dir data/inbox/demo --once

Reads every `.eml` file in `--dir` and feeds it through the exact same parse
+ classify path `POST /inbox` uses (`app.inbox.parser.parse_eml_bytes` and
`app.inbox.classifier.classify_email`) -- no HTTP, no persistence here, just a
local CLI for the demo. This module stays a thin wrapper so the actual logic
lives once, in `app.inbox`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.inbox.classifier import classify_email
from app.inbox.config import default_inbox_classifier_config
from app.inbox.parser import EmailParseError, looks_like_pdf, parse_eml_bytes, select_document


def poll_once(directory: Path) -> int:
    config = default_inbox_classifier_config()
    eml_paths = sorted(directory.glob("*.eml"))
    if not eml_paths:
        print(f"no .eml files found in {directory}")
        return 0

    for path in eml_paths:
        raw = path.read_bytes()
        try:
            parsed = parse_eml_bytes(raw)
        except EmailParseError as exc:
            print(f"{path.name}: parse_error={exc.code}")
            continue
        pdfs = tuple(a for a in parsed.attachments if looks_like_pdf(a))
        selected = select_document(parsed)
        result = classify_email(
            parsed,
            config=config,
            sender_emails=frozenset(),
            allowed_beneficiaries=(),
            pdf_attachments=pdfs,
            document_ambiguous=selected.ambiguous,
            llm=None,
        )
        print(
            f"{path.name}: classification={result.classification} score={result.score} "
            f"reason={result.reason!r}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local .eml inbox poll (no real mailbox).")
    parser.add_argument("--dir", required=True, help="Directory with .eml files to read.")
    parser.add_argument(
        "--once", action="store_true", help="Process the directory once and exit (only mode)."
    )
    args = parser.parse_args(argv)
    # Single-shot is the only supported mode in this MVP; --once is accepted
    # (and required by the documented command) but there is no loop to skip.
    return poll_once(Path(args.dir))


if __name__ == "__main__":
    sys.exit(main())
