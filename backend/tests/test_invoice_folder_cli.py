"""T3.9 — Invoice folder CLI writes decisions.json. No network."""

from __future__ import annotations

import importlib.util
import json
import socket
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from app.config import Settings
from app.graph.folder_batch import (
    FolderBatchError,
    build_runtime_graph_deps,
    run_invoice_folder,
    select_catalog_rows,
)
from app.graph.tracing import NullTrace, make_langsmith_session
from app.models.domain import DecisionRecord
from langgraph.checkpoint.memory import MemorySaver

_GRAPH_TESTS = Path(__file__).with_name("test_invoice_graph.py")
_SPEC = importlib.util.spec_from_file_location("test_invoice_graph", _GRAPH_TESTS)
assert _SPEC is not None and _SPEC.loader is not None
_invoice_graph_tests = importlib.util.module_from_spec(_SPEC)
sys.modules["test_invoice_graph"] = _invoice_graph_tests
_SPEC.loader.exec_module(_invoice_graph_tests)

PAY_CHAT = _invoice_graph_tests.PAY_CHAT
_deps = _invoice_graph_tests._deps


def _fake_deps_factory(tmp_path: Path) -> Callable:
    def factory(_settings: Settings, ledger: tuple) -> object:
        base = _deps(tmp_path)
        return base.__class__(
            extractor=base.extractor,
            verifier=base.verifier,
            jev=base.jev,
            rules=base.rules,
            fx=base.fx,
            ledger=ledger,
            company_name=base.company_name,
            rules_version=base.rules_version,
            model_extractor=base.model_extractor,
            model_verifier=base.model_verifier,
            jev_label=base.jev_label,
            contracts_dir=base.contracts_dir,
        )

    return factory


def test_select_catalog_rows_matches_files_in_folder(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    inv_dir = repo / "data" / "invoices" / "dev"
    inv_dir.mkdir(parents=True)
    (inv_dir / "a.pdf").write_bytes(b"%PDF-1.4\n")
    (inv_dir / "b.txt").write_text("chat\n", encoding="utf-8")
    catalog = [
        {
            "id": "dev-002",
            "path": "data/invoices/dev/b.txt",
            "channel": "chat",
            "received_at": "2026-01-02T10:00:00Z",
            "ledger_seed": [],
        },
        {
            "id": "dev-001",
            "path": "data/invoices/dev/a.pdf",
            "channel": "pdf_text",
            "received_at": "2026-01-01T10:00:00Z",
            "ledger_seed": [],
        },
        {
            "id": "hold-001",
            "path": "data/invoices/holdout/x.pdf",
            "channel": "pdf_text",
            "received_at": "2026-01-03T10:00:00Z",
            "ledger_seed": [],
        },
    ]
    rows = select_catalog_rows(catalog, inv_dir, repo)
    assert [r["id"] for r in rows] == ["dev-001", "dev-002"]


def test_select_unknown_file_raises(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    inv_dir = repo / "data" / "invoices" / "dev"
    inv_dir.mkdir(parents=True)
    (inv_dir / "orphan.pdf").write_bytes(b"%PDF-1.4\n")
    with pytest.raises(FolderBatchError) as exc:
        select_catalog_rows([], inv_dir, repo)
    assert exc.value.code == "unknown_invoice_file"


def test_run_invoice_folder_writes_decisions_json(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    inv_dir = repo / "data" / "invoices" / "dev"
    inv_dir.mkdir(parents=True)
    chat_path = inv_dir / "inv.txt"
    chat_path.write_text(PAY_CHAT, encoding="utf-8")
    catalog_path = repo / "data" / "invoices" / "catalog.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(
            [
                {
                    "id": "dev-cli-1",
                    "path": "data/invoices/dev/inv.txt",
                    "channel": "chat",
                    "received_at": "2026-03-15T12:00:00Z",
                    "ledger_seed": [],
                }
            ]
        ),
        encoding="utf-8",
    )
    out = tmp_path / "decisions.json"
    factory = _fake_deps_factory(tmp_path)
    report = run_invoice_folder(
        inv_dir,
        out,
        repo_root=repo,
        catalog_path=catalog_path,
        settings=Settings(),
        deps_factory=factory,
        tracer=NullTrace(),
        checkpointer=MemorySaver(),
    )
    assert report.processed == 1
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["phase"] == "dev"
    assert len(payload["records"]) == 1
    record = DecisionRecord.model_validate(payload["records"][0])
    assert record.decision == "PAGAR"
    assert record.invoice_id == "dev-cli-1"
    assert record.trace.langsmith_run_id is None


def test_run_folder_uses_null_trace_from_settings(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    inv_dir = repo / "data" / "invoices" / "dev"
    inv_dir.mkdir(parents=True)
    (inv_dir / "inv.txt").write_text(PAY_CHAT, encoding="utf-8")
    catalog_path = repo / "catalog.json"
    catalog_path.write_text(
        json.dumps(
            [
                {
                    "id": "dev-cli-2",
                    "path": "data/invoices/dev/inv.txt",
                    "channel": "chat",
                    "received_at": "2026-03-15T12:00:00Z",
                    "ledger_seed": [],
                }
            ]
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    tracer = make_langsmith_session(Settings())
    assert isinstance(tracer, NullTrace)
    run_invoice_folder(
        inv_dir,
        out,
        repo_root=repo,
        catalog_path=catalog_path,
        settings=Settings(),
        deps_factory=_fake_deps_factory(tmp_path),
        tracer=tracer,
    )
    record = DecisionRecord.model_validate(json.loads(out.read_text())["records"][0])
    assert record.trace.langsmith_run_id is None


def test_build_runtime_graph_deps_imports_without_network() -> None:
    """Factory exists for the CLI; tests inject doubles instead of calling it."""
    assert callable(build_runtime_graph_deps)


def test_eval_run_invoices_main_import_no_socket() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "run_invoices",
        repo_root / "eval" / "run_invoices.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    calls: list[tuple] = []

    class _Guard(socket.socket):
        def __init__(self, *args, **kwargs) -> None:
            calls.append(args)
            raise OSError("network blocked in test")

    old_socket = socket.socket
    socket.socket = _Guard  # type: ignore[misc, assignment]
    try:
        spec.loader.exec_module(module)
    finally:
        socket.socket = old_socket
    assert calls == []
    assert callable(module.main)
