"""T8.1 — POST /invoices passes X-User-Id into LangSmith open_config. No network."""

from __future__ import annotations

from datetime import UTC, datetime

from app.api import create_app
from app.api.production_processor import make_production_processor
from app.graph.deps import GraphDeps
from app.models.rules_config import RulesConfig
from app.persistence import init_database, seed_rules
from app.persistence.sql_store import SqlStore
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import create_engine
from tests.api.support import RULES_PATH
from tests.test_invoice_graph import PAY_CHAT, _deps
from tests.test_tracing import _SYNTH_OWNER, _FakeTrace


def test_post_invoice_passes_x_user_id_to_tracer_open_config(tmp_path) -> None:
    db = tmp_path / "trace_owner.sqlite"
    engine = create_engine(f"sqlite:///{db}")
    init_database(engine)
    store = SqlStore(engine)
    seed_rules(store, RULES_PATH)
    tracer = _FakeTrace()

    def deps_factory(
        _settings: object,
        rules: RulesConfig,
        _ledger: tuple[object, ...],
    ) -> GraphDeps:
        return _deps(tmp_path)

    processor = make_production_processor(
        store,
        deps_factory=deps_factory,
        checkpointer=MemorySaver(),
        tracer=tracer,
        data_root=tmp_path,
    )
    app = create_app(
        store,
        processor,
        clock=lambda: datetime(2026, 3, 4, 12, 0, tzinfo=UTC),
        rate_limit=1000,
    )
    client = TestClient(app, headers={"X-User-Id": _SYNTH_OWNER})

    response = client.post(
        "/invoices",
        data={
            "invoice_id": "INV-T81",
            "channel": "chat",
            "received_at": "2026-03-15T12:00:00Z",
        },
        files={"file": ("chat.txt", PAY_CHAT.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 201
    assert tracer.opened
    metadata, tags = tracer.opened[0]
    assert metadata["owner_id"] == _SYNTH_OWNER
    assert tags == ["invoice", "demo", _SYNTH_OWNER]
