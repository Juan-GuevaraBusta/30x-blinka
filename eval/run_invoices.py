#!/usr/bin/env python3
"""CLI: process an invoice folder through the graph and write decisions.json (T3.9)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.config import load_settings
from app.graph import make_langsmith_session
from app.graph.folder_batch import FolderBatchError, repo_root_from_module, run_invoice_folder


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the invoice agent on each file in a folder; write decisions.json.",
    )
    parser.add_argument(
        "invoices_dir",
        nargs="?",
        default="data/invoices/dev",
        help="Directory with invoice files (default: data/invoices/dev).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="decisions.json",
        help="Output JSON path (default: decisions.json).",
    )
    parser.add_argument(
        "--data-root",
        default=None,
        help="Repo root with data/ (default: auto-detect from package layout).",
    )
    parser.add_argument(
        "--catalog",
        default="data/invoices/catalog.json",
        help="Catalog JSON path relative to data-root (default: data/invoices/catalog.json).",
    )
    parser.add_argument(
        "--phase",
        choices=("dev", "eval", "demo"),
        default="dev",
        help="LangSmith phase tag (default: dev).",
    )
    args = parser.parse_args(argv)

    root = Path(args.data_root).resolve() if args.data_root else repo_root_from_module()
    invoices_dir = Path(args.invoices_dir)
    if not invoices_dir.is_absolute():
        invoices_dir = (root / invoices_dir).resolve()
    catalog_path = Path(args.catalog)
    if not catalog_path.is_absolute():
        catalog_path = (root / catalog_path).resolve()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path

    settings = load_settings()
    tracer = make_langsmith_session(settings)
    try:
        report = run_invoice_folder(
            invoices_dir,
            output_path,
            repo_root=root,
            catalog_path=catalog_path,
            phase=args.phase,
            settings=settings,
            tracer=tracer,
        )
    except FolderBatchError as exc:
        print(f"error: {exc.code} {exc.detail}".strip(), file=sys.stderr)
        return 2

    print(f"processed={report.processed} output={report.output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
