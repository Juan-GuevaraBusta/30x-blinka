"""T5.7 — Regression: `app.extraction` must not depend on a `backend.*` import.

`backend/app/extraction/__init__.py` used to import `backend.app.extraction.X`,
which only resolves when `backend` itself is importable as a top-level package
(e.g. by accident, when the current working directory happens to be the repo
root). That broke `cd backend && pytest` and `python eval/run_invoices.py`
(run from the repo root, where `eval/` -- not the repo root -- lands on
sys.path). See docs/T5_7_SPEC.md (D055) and
eval/reports/g3_closure_2026-10-17.md line 14.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
EVAL_RUN_INVOICES = REPO_ROOT / "eval" / "run_invoices.py"


def test_app_extraction_imports_without_module_not_found_error() -> None:
    """Importing `app.extraction` must never require a `backend` top-level package."""
    import app.extraction as extraction

    assert callable(extraction.ingest_path)
    assert callable(extraction.extract_document)
    assert callable(extraction.normalize_document_text)


def test_eval_run_invoices_help_exits_zero_from_repo_root() -> None:
    """`python eval/run_invoices.py --help`, invoked from the repo root, must exit 0."""
    result = subprocess.run(
        [sys.executable, str(EVAL_RUN_INVOICES), "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "usage" in result.stdout.lower()


def test_eval_run_invoices_help_exits_zero_from_backend_dir() -> None:
    """Same CLI entrypoint must also exit 0 when invoked with `backend/` as cwd.

    This mirrors the `cd backend && pytest` invocation style: the import chain
    must not depend on which directory happens to be the process cwd.
    """
    result = subprocess.run(
        [sys.executable, str(EVAL_RUN_INVOICES), "--help"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "usage" in result.stdout.lower()
