"""T3.8 — LangSmith trace id on the decision record. No network."""

from __future__ import annotations

import importlib
import importlib.util
import socket
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, get_type_hints

import pytest
from app.config import ConfigError, Settings
from app.graph import compile_invoice_graph, run_invoice
from app.models.domain import TraceRef
from langgraph.checkpoint.memory import MemorySaver

_GRAPH_TESTS = Path(__file__).with_name("test_invoice_graph.py")
_SPEC = importlib.util.spec_from_file_location("test_invoice_graph", _GRAPH_TESTS)
assert _SPEC is not None and _SPEC.loader is not None
_invoice_graph_tests = importlib.util.module_from_spec(_SPEC)
sys.modules["test_invoice_graph"] = _invoice_graph_tests
_SPEC.loader.exec_module(_invoice_graph_tests)

PAY_CHAT = _invoice_graph_tests.PAY_CHAT
_deps = _invoice_graph_tests._deps

_RUN_ID = "00000000-0000-4000-8000-000000000001"
_RUN_URL = "https://smith.langchain.com/r/00000000-0000-4000-8000-000000000001"
_TRACING_SOURCE = Path(__file__).resolve().parents[1] / "app" / "graph" / "tracing.py"


class _FakeTrace:
    def __init__(
        self,
        ref: TraceRef | None = None,
        *,
        boom: BaseException | None = None,
    ) -> None:
        self.ref = ref
        self.boom = boom
        self.opened: list[tuple[dict[str, str], list[str]]] = []
        self.finished: list[str] = []

    def open_config(self, *, metadata: dict[str, str], tags: list[str]) -> dict:
        self.opened.append((dict(metadata), list(tags)))
        return {"metadata": dict(metadata), "tags": list(tags)}

    def finish(self, decision: str) -> TraceRef | None:
        self.finished.append(decision)
        if self.boom is not None:
            raise self.boom
        return self.ref


def _pay(tmp_path: Path, **kwargs: object):
    deps = _deps(tmp_path)
    saver = MemorySaver()
    thread_id = "t-trace"
    record = run_invoice(
        deps,
        raw=PAY_CHAT.encode("utf-8"),
        channel="chat",
        invoice_id="INV-G1",
        received_at=datetime(2026, 3, 15, 12, 0, tzinfo=UTC),
        checkpointer=saver,
        thread_id=thread_id,
        **kwargs,  # type: ignore[arg-type]
    )
    return record, saver, deps, thread_id


def test_null_trace_is_empty_and_silent() -> None:
    from app.graph.tracing import NullTrace

    tracer = NullTrace()
    assert tracer.open_config(metadata={"invoice_id": "INV-G1"}, tags=["invoice"]) == {}
    assert tracer.finish("PAGAR") is None


def test_run_without_tracer_leaves_trace_empty(tmp_path: Path) -> None:
    record, _, _, _ = _pay(tmp_path)
    assert record.decision == "PAGAR"
    assert record.trace.langsmith_run_id is None
    assert record.trace.url is None


def test_fake_tracer_stores_run_id_on_record_and_checkpoint(tmp_path: Path) -> None:
    tracer = _FakeTrace(TraceRef(langsmith_run_id=_RUN_ID, url=_RUN_URL))
    record, saver, deps, thread_id = _pay(tmp_path, tracer=tracer)
    assert record.decision == "PAGAR"
    assert record.trace.langsmith_run_id == _RUN_ID
    assert record.trace.url == _RUN_URL
    assert tracer.finished == ["PAGAR"]
    graph = compile_invoice_graph(deps, saver)
    state = graph.get_state({"configurable": {"thread_id": thread_id}})
    assert state.values["record"]["trace"]["langsmith_run_id"] == _RUN_ID


def test_finish_error_keeps_business_decision(tmp_path: Path) -> None:
    tracer = _FakeTrace(boom=RuntimeError("langsmith_down"))
    record, _, _, _ = _pay(tmp_path, tracer=tracer)
    assert record.decision == "PAGAR"
    assert record.trace.langsmith_run_id is None
    assert "langsmith_down" not in record.summary


def test_metadata_has_invoice_and_phase_not_document(tmp_path: Path) -> None:
    tracer = _FakeTrace(TraceRef(langsmith_run_id=_RUN_ID, url=_RUN_URL))
    record, _, _, _ = _pay(tmp_path, tracer=tracer)
    assert record.decision == "PAGAR"
    assert tracer.opened
    metadata, tags = tracer.opened[0]
    assert metadata["invoice_id"] == "INV-G1"
    assert metadata["phase"] == "dev"
    assert "rules_version" in metadata
    assert "model_extractor" in metadata
    assert "model_verifier" in metadata
    assert "jev" in metadata
    blob = " ".join([*metadata.values(), *tags])
    assert "Demo SA" not in blob
    assert "test-key" not in blob
    assert tags == ["invoice", "dev"]


def test_phase_eval_reaches_metadata(tmp_path: Path) -> None:
    tracer = _FakeTrace()
    _pay(tmp_path, tracer=tracer, phase="eval")
    metadata, tags = tracer.opened[0]
    assert metadata["phase"] == "eval"
    assert tags == ["invoice", "eval"]
    hints = get_type_hints(run_invoice)
    assert hints["phase"] == Literal["dev", "eval", "demo"]


_SYNTH_OWNER = "usr_synth_001"


def test_owner_id_in_metadata_and_tags_when_set(tmp_path: Path) -> None:
    tracer = _FakeTrace()
    _pay(tmp_path, tracer=tracer, owner_id=_SYNTH_OWNER)
    metadata, tags = tracer.opened[0]
    assert metadata["owner_id"] == _SYNTH_OWNER
    assert tags == ["invoice", "dev", _SYNTH_OWNER]
    blob = " ".join([*metadata.values(), *tags])
    assert "Demo SA" not in blob
    assert "test-key" not in blob


def test_owner_id_omitted_when_none_or_blank(tmp_path: Path) -> None:
    for owner_kw in ({}, {"owner_id": None}, {"owner_id": ""}, {"owner_id": "   "}):
        tracer = _FakeTrace()
        _pay(tmp_path, tracer=tracer, **owner_kw)
        metadata, tags = tracer.opened[0]
        assert "owner_id" not in metadata
        assert tags == ["invoice", "dev"]


def test_settings_reads_four_langsmith_keys() -> None:
    filled = Settings.from_mapping(
        {
            "LANGSMITH_TRACING": "true",
            "LANGSMITH_API_KEY": "synthetic-not-printed",
            "LANGSMITH_PROJECT": "blinka-invoice-agent-eval",
            "LANGSMITH_ENDPOINT": "https://example.test",
        }
    )
    assert filled.langsmith_tracing is True
    assert filled.langsmith_api_key == "synthetic-not-printed"
    assert filled.langsmith_project == "blinka-invoice-agent-eval"
    assert filled.langsmith_endpoint == "https://example.test"

    empty = Settings.from_mapping({})
    assert empty.langsmith_tracing is False
    assert empty.langsmith_api_key == ""
    assert empty.langsmith_project == "blinka-invoice-agent-dev"
    assert empty.langsmith_endpoint == ""

    with pytest.raises(ConfigError) as exc:
        Settings.from_mapping({"LANGSMITH_TRACING": "yes"})
    assert exc.value.code == "invalid_bool"


def test_make_langsmith_session_off_is_null_trace() -> None:
    from app.graph.tracing import NullTrace, make_langsmith_session

    session = make_langsmith_session(Settings())
    assert isinstance(session, NullTrace)
    assert session.finish("PAGAR") is None
    assert not hasattr(session, "_client")


def test_graph_import_exports_tracing_without_sockets(monkeypatch: pytest.MonkeyPatch) -> None:
    source = _TRACING_SOURCE.read_text(encoding="utf-8")
    assert "lsv2_" not in source
    assert "sk-" not in source
    assert "test-key" not in source

    connects: list[object] = []

    def _refuse_connect(self: socket.socket, address: object) -> None:
        connects.append(address)
        raise AssertionError("socket connect")

    monkeypatch.setattr(socket.socket, "connect", _refuse_connect)
    graph = importlib.reload(importlib.import_module("app.graph"))
    assert graph.run_invoice is run_invoice or callable(graph.run_invoice)
    assert graph.NullTrace is not None
    assert callable(graph.make_langsmith_session)
    assert connects == []


def test_finish_builds_run_url_with_client_when_run_has_none() -> None:
    # Production records had langsmith_run_id but url=None, so the UI had no
    # "Ver traza" link. The SDK's get_run_url fills it (best effort).
    from types import SimpleNamespace

    from app.graph.tracing import _LangSmithSession

    session = object.__new__(_LangSmithSession)
    session._failed = False
    session._project_name = "blinka"
    run = SimpleNamespace(trace_id="t-1", id="r-1", url=None)
    session._tracer = SimpleNamespace(latest_run=run)
    session._client = SimpleNamespace(
        get_run_url=lambda *, run, project_name: f"https://smith.example/{project_name}/{run.id}"
    )

    ref = session.finish("PAGAR")

    assert ref is not None
    assert ref.langsmith_run_id == "t-1"
    assert ref.url == "https://smith.example/blinka/r-1"


def test_finish_keeps_run_id_when_url_lookup_fails() -> None:
    from types import SimpleNamespace

    from app.graph.tracing import _LangSmithSession

    def boom(**_kw: object) -> str:
        raise RuntimeError("network")

    session = object.__new__(_LangSmithSession)
    session._failed = False
    session._project_name = "blinka"
    session._tracer = SimpleNamespace(
        latest_run=SimpleNamespace(trace_id="t-2", id="r-2", url=None)
    )
    session._client = SimpleNamespace(get_run_url=boom)

    ref = session.finish("ESCALAR")

    assert ref is not None
    assert ref.langsmith_run_id == "t-2"
    assert ref.url is None
