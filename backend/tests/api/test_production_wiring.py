"""Production ASGI wiring: tracing and the agreement-draft LLM (live scenario defects).

`create_production_app` must hand the processor a LangSmith tracer when the
environment enables it (NullTrace otherwise), and must give `create_app` the
real extractor-role LLM for `POST /agreements/draft` instead of the empty
stand-in. Both are best-effort: missing config never breaks boot or processing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from app.api import asgi
from app.api.production_processor import make_production_processor
from app.api.schemas import InvoiceUpload
from app.graph.tracing import NullTrace
from app.llm import LlmClient
from tests.api.support import RULES_PATH, TEST_ADMIN_KEY, make_record

_LLM_ENV = {
    "LLM_API_KEY": "test-llm-key",
    "LLM_BASE_URL": "https://llm.example.invalid/v1",
    "EXTRACTOR_MODEL": "fake/extractor",
}


def _capture_wiring(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    captured: dict[str, Any] = {}
    real_processor = asgi.make_production_processor
    real_create_app = asgi.create_app

    def spy_processor(store, **kwargs):
        captured["processor_kwargs"] = kwargs
        return real_processor(store, **kwargs)

    def spy_create_app(store, processor, **kwargs):
        captured["app_kwargs"] = kwargs
        return real_create_app(store, processor, **kwargs)

    monkeypatch.setattr(asgi, "make_production_processor", spy_processor)
    monkeypatch.setattr(asgi, "create_app", spy_create_app)
    return captured


def _boot(tmp_path, extra: dict[str, str]) -> None:
    mapping = {
        "DATABASE_URL": f"sqlite:///{tmp_path / 'wiring.sqlite'}",
        "ADMIN_API_KEY": TEST_ADMIN_KEY,
        **extra,
    }
    asgi.create_production_app(mapping, rules_path=RULES_PATH, cors_origins="")


def _tracer_from(captured: dict[str, Any]):
    kwargs = captured["processor_kwargs"]
    factory = kwargs.get("tracer_factory")
    assert factory is not None, "production processor must be wired with a tracer factory"
    return factory()


def test_production_app_wires_langsmith_tracer_when_enabled(tmp_path, monkeypatch) -> None:
    captured = _capture_wiring(monkeypatch)
    _boot(tmp_path, {"LANGSMITH_TRACING": "true", "LANGSMITH_API_KEY": "ls-test-key"})

    tracer = _tracer_from(captured)

    assert not isinstance(tracer, NullTrace)
    assert hasattr(tracer, "open_config") and hasattr(tracer, "finish")


def test_production_app_uses_null_trace_when_tracing_disabled(tmp_path, monkeypatch) -> None:
    captured = _capture_wiring(monkeypatch)
    _boot(tmp_path, {})

    assert isinstance(_tracer_from(captured), NullTrace)


def test_production_app_wires_real_agreement_llm(tmp_path, monkeypatch) -> None:
    captured = _capture_wiring(monkeypatch)
    _boot(tmp_path, _LLM_ENV)

    llm = captured["app_kwargs"].get("agreement_llm")

    assert isinstance(llm, LlmClient)
    assert llm.role == "extractor"
    assert llm.model == "fake/extractor"


def test_production_app_without_llm_config_still_boots(tmp_path, monkeypatch) -> None:
    """No LLM key: boot never fails; the draft endpoint keeps its fail-closed stand-in."""
    captured = _capture_wiring(monkeypatch)
    _boot(tmp_path, {})

    assert captured["app_kwargs"].get("agreement_llm") is None


def test_tracer_factory_failure_never_breaks_processing(tmp_path, monkeypatch) -> None:
    """A tracer that cannot be built falls back to no tracing; the invoice is still decided."""
    from app.api import production_processor as pp

    seen: dict[str, Any] = {}

    def broken_factory():
        raise RuntimeError("langsmith down")

    def fake_run_invoice(deps, **kwargs):
        seen["tracer"] = kwargs.get("tracer")
        return make_record(invoice_id=kwargs["invoice_id"])

    monkeypatch.setattr(pp, "run_invoice", fake_run_invoice)
    monkeypatch.setattr(pp, "settled_ledger_from_store", lambda store, fx=None: pp.Ledger.empty())
    monkeypatch.setattr(pp, "effective_rules_and_contracts", lambda store: (None, {}))
    processor = make_production_processor(
        object(),  # type: ignore[arg-type]  never touched: the graph is faked
        data_root=RULES_PATH.resolve().parent.parent,
        deps_factory=lambda s, r, ledger: object(),  # type: ignore[arg-type,return-value]
        tracer_factory=broken_factory,
    )

    record = processor(
        InvoiceUpload(
            invoice_id="INV-TRACE-1",
            channel="chat",
            received_at=datetime(2026, 3, 1, tzinfo=UTC),
            content=b"x",
        ),
        "owner-1",
    )

    assert record.invoice_id == "INV-TRACE-1"
    assert isinstance(seen["tracer"], NullTrace)
